using Alpaca.Markets;
using DotNetEnv;
using Microsoft.AspNetCore.Mvc;
using System.Linq;

Env.Load();

// Web API
var builder = WebApplication.CreateBuilder(args);


// Register CredentialProvider as singleton (SecretStore is injected into it)
builder.Services.AddDataProtection();
builder.Services.AddSingleton<SecretStore>();
builder.Services.AddSingleton<CredentialProvider>();
builder.Services.AddSingleton<Portfolio>(Portfolio.Load());



// Add CORS
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.WithOrigins("http://localhost:5173", "http://127.0.0.1:5173") // Vite default port
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});
var app = builder.Build();
app.UseHttpsRedirection();
app.UseStaticFiles();              // serve wwwroot
app.UseCors();



app.MapPost("/settings/credentials", (SecretStore store, CredentialProvider provider, CredentialsRequest req) =>
{
    var secret = req.Secret;
    var key = req.Key;
    if (string.IsNullOrEmpty(secret) || string.IsNullOrEmpty(key))
    {
        return Results.BadRequest("Secret and key must be provided.");
    }
    store.Save(secret, key);

    provider.GetOrCreateClient();
    return Results.Ok("Credentials saved successfully.");

    

});

// Stock Bars getter functions

app.MapGet("/bars/{symbol}", GetBars);
static async Task<IResult> GetBars(CredentialProvider provider, string symbol,  int? hours) 
{
    var dataClient = provider.GetOrCreateClient();
    if (dataClient == null)
    {
        return Results.Unauthorized();
    }

    // Returns Alpaca IBar Objects , not JSON. 
    symbol = symbol.Trim().ToUpper();
    var lookback = hours ?? 24;
    var now = DateTime.UtcNow.AddMinutes(-15);
    var start = now.AddHours(-lookback);

    // create request
    var req = new HistoricalBarsRequest(
        symbol, start, now, BarTimeFrame.Hour);
    var res = await dataClient.ListHistoricalBarsAsync(req);
    List<int> closes = new List<int>();
    foreach (var bar in res.Items)
    {
        closes.Add((int)bar.Close);
    }
    return Results.Ok(closes);
};


app.MapGet("/bars/daily/{symbol}", GetDailyBars);
static async Task<IResult> GetDailyBars(CredentialProvider provider, string symbol,  int? days) 
{
    var dataClient = provider.GetOrCreateClient();
    if (dataClient == null)
    {
        return Results.Unauthorized();
    }

    var symbols = symbol.Split(',').Select(s => s.Trim().ToUpper()).ToList();
    var lookback = days ?? 30;
    var now = DateTime.UtcNow.AddMinutes(-15);
    var start = now.AddDays(-lookback);

    if (symbols.Count == 1)
    {
        var req = new HistoricalBarsRequest(symbols[0], start, now, BarTimeFrame.Day);
        var res = await dataClient.ListHistoricalBarsAsync(req);
        return Results.Ok(res.Items.Select(b => new { Time = b.TimeUtc, Price = b.Close }));
    }
    else
    {
        var req = new HistoricalBarsRequest(symbols, start, now, BarTimeFrame.Day);
        var res = await dataClient.GetHistoricalBarsAsync(req);
        var dict = res.Items.ToDictionary(
            kvp => kvp.Key,
            kvp => kvp.Value.Select(b => new { Time = b.TimeUtc, Price = b.Close })
        );
        return Results.Ok(dict);
    }
};

app.MapGet("/bars/minutes/{symbol}", GetMinuteBars);
static async Task<IResult> GetMinuteBars(CredentialProvider provider, string symbol, int? minutes)
{
    var dataClient = provider.GetOrCreateClient();
    if (dataClient == null) return Results.Unauthorized();

    var symbols = symbol.Split(',', StringSplitOptions.RemoveEmptyEntries)
                        .Select(s => s.Trim().ToUpperInvariant())
                        .ToList();

    var requestedMinutes = minutes ?? 60;
    var now = DateTime.UtcNow.AddMinutes(-15);

    int takeCount;
    TimeSpan lookback;

    if (requestedMinutes == 960) // Frontend "1D"
    {
        takeCount = 960;
        lookback = TimeSpan.FromDays(7); // Plenty of lookback to cross weekends
    }
    else if (requestedMinutes == 4800) // Frontend "1W"
    {
        takeCount = 4800;
        lookback = TimeSpan.FromDays(14); // Plenty of lookback to cross weekends
    }
    else
    {
        takeCount = requestedMinutes;
        lookback = TimeSpan.FromMinutes(requestedMinutes * 3);
    }

    var start = now - lookback;
    static List<object> MostRecentN(IEnumerable<IBar> bars, int n) =>
        bars.OrderBy(b => b.TimeUtc)
            .Select(b => new { Time = b.TimeUtc, Price = b.Close })
            .TakeLast(n)
            .Cast<object>()
            .ToList();

    if (symbols.Count == 1)
    {
        var bars = new List<IBar>();
        var req = new HistoricalBarsRequest(symbols[0], start, now, BarTimeFrame.Minute).WithPageSize(10000);
        do 
        {
            var page = await dataClient.ListHistoricalBarsAsync(req);
            bars.AddRange(page.Items);
            req = req.WithPageToken(page.NextPageToken);
        }
        while (req.Pagination.Token is not null);
     
        return Results.Ok(MostRecentN(bars, takeCount));
    }
    else
    {
        var all = new Dictionary<string, List<IBar>>(StringComparer.OrdinalIgnoreCase);
        var req = new HistoricalBarsRequest(symbols, start, now, BarTimeFrame.Minute);
        do 
        {
            var res = await dataClient.GetHistoricalBarsAsync(req);
            foreach (var kvp in res.Items)
            {
                if (!all.TryGetValue(kvp.Key, out var bars))
                {
                    all[kvp.Key] = bars = new List<IBar>();
                }
                bars.AddRange(kvp.Value);
            }
            req = req.WithPageToken(res.NextPageToken);
        }
        while (req.Pagination.Token is not null);
       

        return Results.Ok(all);
    }
};

app.MapGet("/snapshots", async (CredentialProvider provider, [FromQuery] string symbols) => {
    var dataClient = provider.GetOrCreateClient();
    if (dataClient == null) return Results.Unauthorized();

    var symbolList = symbols.Split(',').Select(s => s.Trim().ToUpper()).ToList();
    var snapshots = await dataClient.ListSnapshotsAsync(new LatestMarketDataListRequest(symbolList));
    
    var res = snapshots.ToDictionary(
        kvp => kvp.Key,
        kvp => new {
            Price = kvp.Value.MinuteBar?.Close ?? 0,
            Timestamp = kvp.Value.MinuteBar?.TimeUtc
        }
    );
    return Results.Ok(res);
});

app.MapGet("/portfolio/pnl", async ([FromServices] Portfolio portfolio, CredentialProvider provider) => {
    var dataClient = provider.GetOrCreateClient();
    if (dataClient == null) return Results.Unauthorized();

    if (portfolio.Investments.Count == 0) {
        return Results.Ok(new { PnLPercent = 0, RealizedPnL = portfolio.RealizedPnL });
    }

    var symbols = portfolio.Investments.Keys.ToList();
    var snapshots = await dataClient.ListSnapshotsAsync(new LatestMarketDataListRequest(symbols));
    
    var currentPrices = snapshots.ToDictionary(
        kvp => kvp.Key,
        kvp => kvp.Value.MinuteBar?.Close ?? 0
    );

    var pnlPercent = portfolio.ComputePnL(currentPrices);
    return Results.Ok(new { 
        PnLPercent = pnlPercent, 
        RealizedPnL = portfolio.RealizedPnL,
        Investments = portfolio.Investments,
        CurrentPrices = currentPrices
    });
});
 
app.MapGet("/portfolio", ([FromServices] Portfolio portfolio) => Results.Ok(portfolio));

app.MapPost("/portfolio/transaction", ([FromServices] Portfolio portfolio, Transaction transaction) => {
    try {
        portfolio.ProcessTransaction(transaction);
        return Results.Ok(portfolio);
    } catch (Exception ex) {
        return Results.BadRequest(ex.Message);
    }
});


app.MapPost("/portfolio/reset", ([FromServices] Portfolio portfolio) => {
    portfolio.Reset();
    return Results.Ok(portfolio);
});

app.Run();

internal record CredentialsRequest(string Key, string Secret);

