using Alpaca.Markets;
using DotNetEnv;
using Microsoft.AspNetCore.Mvc;

Env.Load();

// Web API
var builder = WebApplication.CreateBuilder(args);


// Register CredentialProvider as singleton (SecretStore is injected into it)
builder.Services.AddDataProtection();
builder.Services.AddSingleton<SecretStore>();
builder.Services.AddSingleton<CredentialProvider>();



// Add CORS
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.WithOrigins("http://localhost:5173") // Vite default port
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

    symbol = symbol.Trim().ToUpper();
    var lookback = days ?? 30;
    var now = DateTime.UtcNow.AddMinutes(-15);
    var start = now.AddDays(-lookback);

    var req = new HistoricalBarsRequest(symbol, start, now, BarTimeFrame.Day);
    var res = await dataClient.ListHistoricalBarsAsync(req);
    
    return Results.Ok(res.Items.Select(b => new { Time = b.TimeUtc, Price = b.Close }));
};

app.MapGet("/bars/minutes/{symbol}", GetMinuteBars);
static async Task<IResult> GetMinuteBars(CredentialProvider provider, string symbol,int? minutes) 
{
    var dataClient = provider.GetOrCreateClient();
    if (dataClient == null)
    {
        return Results.Unauthorized();
    }
    symbol = symbol.Trim().ToUpper();
    var lookback = minutes ?? 60;
    var now = DateTime.UtcNow.AddMinutes(-15);
    var start = now.AddMinutes(-lookback);

    var req = new HistoricalBarsRequest(symbol, start, now, BarTimeFrame.Minute);
    var res = await dataClient.ListHistoricalBarsAsync(req);

    return Results.Ok(res.Items.Select(b => new { Time = b.TimeUtc, Price = b.Close }) );
};

app.Run();

internal record CredentialsRequest(string Key, string Secret);

