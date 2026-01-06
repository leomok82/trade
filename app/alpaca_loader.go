package main

import (
	"context"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/alpacahq/alpaca-trade-api-go/v3/marketdata"
	"github.com/alpacahq/alpaca-trade-api-go/v3/marketdata/stream"
)

// DataClient interface
type DataClient interface {
	GetHistory(symbols []string, nDays int, interval string) (interface{}, error)
	// Go interface return types are tricky when replicating dynamic languages.
	// Python returns DataFrames. Here we might return raw bars.
}

// StockClient
type StockClient struct {
	client *marketdata.Client
}

func NewStockClient() *StockClient {
	return &StockClient{
		client: marketdata.NewClient(marketdata.ClientOpts{
			APIKey:    AlpacaKey,
			APISecret: AlpacaSecret,
			Feed:      marketdata.IEX, // Matching feed=DataFeed.IEX from Python
		}),
	}
}

func (sc *StockClient) UsTradingHours(day time.Time) (time.Time, time.Time) {
	// Ensure day is in UTC
	day = day.UTC()

	// Create start and end times
	// Python: datetime(day.year, day.month, day.day, 13, 30, tzinfo=timezone.utc) # 9:30 AM ET -> 13:30 UTC
	// Python: end = 20:00 UTC -> 4:00 PM ET

	start := time.Date(day.Year(), day.Month(), day.Day(), 13, 30, 0, 0, time.UTC)
	end := time.Date(day.Year(), day.Month(), day.Day(), 20, 0, 0, 0, time.UTC)

	return start, end
}

// GetHistory fetches bar history
// Note: Python returns pd.DataFrame. Go will return []marketdata.Bar (or a struct wrapping it),
// as DataFrame isn't a native Go construct.
func (sc *StockClient) GetHistory(symbols []string, lookback int, end *time.Time, interval string) (map[string][]marketdata.Bar, error) {
	var endTime time.Time
	if end == nil {
		endTime = time.Now().UTC()
	} else {
		endTime = *end
	}

	_, tradingEnd := sc.UsTradingHours(endTime)
	// lookback days ago
	tradingStart, _ := sc.UsTradingHours(endTime.AddDate(0, 0, -lookback))

	var timeframe marketdata.TimeFrame
	switch strings.ToLower(interval) {
	case "minute":
		timeframe = marketdata.OneMin
	case "hour":
		timeframe = marketdata.OneHour
	default:
		timeframe = marketdata.OneDay
	}

	req := marketdata.GetBarsRequest{
		TimeFrame: timeframe,
		Start:     tradingStart,
		End:       tradingEnd,
		Feed:      marketdata.IEX,
	}

	bars, err := sc.client.GetMultiBars(symbols, req)
	if err != nil {
		return nil, err
	}

	return bars, nil
}

// OptionsClient
type OptionsClient struct {
	client *marketdata.Client
}

func NewOptionsClient() *OptionsClient {
	return &OptionsClient{
		client: marketdata.NewClient(marketdata.ClientOpts{
			APIKey:    AlpacaKey,
			APISecret: AlpacaSecret,
		}),
	}
}

func (oc *OptionsClient) UsTradingHours(day time.Time) (time.Time, time.Time) {
	day = day.UTC()
	start := time.Date(day.Year(), day.Month(), day.Day(), 13, 30, 0, 0, time.UTC)
	end := time.Date(day.Year(), day.Month(), day.Day(), 20, 0, 0, 0, time.UTC)
	return start, end
}

func (oc *OptionsClient) GetHistory(symbols []string, nDays int, interval string) (map[string][]marketdata.OptionBar, error) {
	day := time.Now().UTC().AddDate(0, 0, -nDays)
	start, _ := oc.UsTradingHours(day)

	// replicate end time logic: now - 16 mins
	end := time.Now().UTC().Add(-16 * time.Minute)

	var timeframe marketdata.TimeFrame
	switch strings.ToLower(interval) {
	case "minute":
		timeframe = marketdata.OneMin
	case "hour":
		timeframe = marketdata.OneHour
	default:
		timeframe = marketdata.OneDay
	}

	req := marketdata.GetOptionBarsRequest{
		TimeFrame: timeframe,
		Start:     start,
		End:       end,
		// Feed removed as it is not in GetOptionBarsRequest
	}

	bars, err := oc.client.GetMultiOptionBars(symbols, req)
	if err != nil {
		return nil, err
	}

	return bars, nil
}

type LiveDataClient struct {
	client    *stream.StocksClient
	latest    *stream.Quote
	latestMut sync.RWMutex
	ctx       context.Context
	cancel    context.CancelFunc
}

func NewLiveDataClient() *LiveDataClient {
	ctx, cancel := context.WithCancel(context.Background())
	return &LiveDataClient{
		ctx:    ctx,
		cancel: cancel,
	}
}

func (lc *LiveDataClient) quoteHandler(q stream.Quote) {
	lc.latestMut.Lock()
	defer lc.latestMut.Unlock()
	lc.latest = &q // Keep as pointer to match lc.latest type
}

func (lc *LiveDataClient) GetLatestQuote() (*stream.Quote, bool) {
	lc.latestMut.RLock()
	defer lc.latestMut.RUnlock()
	if lc.latest == nil {
		return nil, false
	}
	// return a copy to avoid races if caller holds it
	q := *lc.latest
	return &q, true
}

// GetQuote starts the websocket and subscribes to quotes.
func (lc *LiveDataClient) GetQuote(symbols []string) {
	c := stream.NewStocksClient(
		marketdata.Feed(""), // Empty feed
		stream.WithCredentials(AlpacaKey, AlpacaSecret),
		stream.WithBaseURL("wss://stream.data.alpaca.markets/v2/test"),
		stream.WithQuotes(lc.quoteHandler, symbols...),
	)

	lc.client = c

	go func() {
		// Connect keeps connection alive / reconnects; blocks until first connect succeeds/fails :contentReference[oaicite:4]{index=4}
		if err := c.Connect(lc.ctx); err != nil {
			log.Printf("Stream terminated: %v", err)
		}
	}()
}

func (lc *LiveDataClient) Stop() {
	lc.cancel()
}
