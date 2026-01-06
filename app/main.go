package main

import (
	"fmt"
	"time"
)

func main() {
	// 1. Load Config
	LoadConfig()
	fmt.Println("Config loaded.")

	// 2. Test StockClient
	fmt.Println("--- Testing StockClient ---")
	stockClient := NewStockClient()
	// Test with a common symbol like AAPL, lookback 1 day
	// Note: We need a valid symbol.
	symbols := []string{"AAPL"}
	now := time.Now()
	bars, err := stockClient.GetHistory(symbols, 1, &now, "hour")
	if err != nil {
		fmt.Printf("StockClient Error: %v\n", err)
	} else {
		fmt.Printf("Fetched %d bars for AAPL\n", len(bars["AAPL"]))
		if len(bars["AAPL"]) > 0 {
			fmt.Printf("First bar: %+v\n", bars["AAPL"][0])
		}
	}

}
