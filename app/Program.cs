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
static async Task<IResult> GetMinuteBars(CredentialProvider provider, string symbol,int? minutes) 
{
    var dataClient = provider.GetOrCreateClient();
    if (dataClient == null)
    {
        return Results.Unauthorized();
    }
    var symbols = symbol.Split(',').Select(s => s.Trim().ToUpper()).ToList();
    var lookback = minutes ?? 60;
    var now = DateTime.UtcNow.AddMinutes(-15);
    var start = now.AddMinutes(-lookback);

    if (symbols.Count == 1)
    {
        var req = new HistoricalBarsRequest(symbols[0], start, now, BarTimeFrame.Minute);
        var res = await dataClient.ListHistoricalBarsAsync(req);
        return Results.Ok(res.Items.Select(b => new { Time = b.TimeUtc, Price = b.Close }));
    }
    else
    {
        var req = new HistoricalBarsRequest(symbols, start, now, BarTimeFrame.Minute);
        var res = await dataClient.GetHistoricalBarsAsync(req);
        var dict = res.Items.ToDictionary(
            kvp => kvp.Key,
            kvp => kvp.Value.Select(b => new { Time = b.TimeUtc, Price = b.Close })
        );
        return Results.Ok(dict);
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

