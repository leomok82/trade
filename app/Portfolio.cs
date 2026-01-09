using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

public record Transaction(string Symbol, int Quantity, decimal TransactionPrice, DateTime TransactionDate, bool Buy);

public class Investment
{
    public string Symbol { get; set; } = string.Empty;
    public int Quantity { get; set; }
    public decimal AverageCost { get; set; }

    public void Update(Transaction transaction)
    {
        if (transaction.Buy)
        {
            decimal totalCost = (Quantity * AverageCost) + (transaction.Quantity * transaction.TransactionPrice);
            Quantity += transaction.Quantity;
            if (Quantity > 0)
            {
                AverageCost = totalCost / Quantity;
            }
        }
        else
        {
            if (transaction.Quantity > Quantity)
            {
                throw new InvalidOperationException("Not enough quantity to sell.");
            }
            // Selling doesn't change AverageCost, just Quantity
            Quantity -= transaction.Quantity;
        }
    }

}

public class Portfolio
{
    private static readonly string Dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".trade");
    private static readonly string Filepath = Path.Combine(Dir, "portfolio.json");

    public decimal TotalAssets { get; set; } = 0;
    public decimal RealizedPnL { get; set; } = 0;
    public Dictionary<string, Investment> Investments { get; set; } = new();


    public void ProcessTransaction(Transaction transaction)
    {
        transaction = transaction with { Symbol = transaction.Symbol.Trim().ToUpper() };

        if (!Investments.TryGetValue(transaction.Symbol, out var investment))
        {
            if (!transaction.Buy) throw new InvalidOperationException("Cannot sell an investment you don't own.");
            investment = new Investment { Symbol = transaction.Symbol };
            Investments[transaction.Symbol] = investment;
        }

        investment.Update(transaction);

        // Update net value
        if (transaction.Buy)
        {
            TotalAssets += transaction.Quantity * transaction.TransactionPrice;
        }
        else {
            RealizedPnL += transaction.Quantity * transaction.TransactionPrice - transaction.Quantity * investment.AverageCost;
            TotalAssets += transaction.Quantity * investment.AverageCost - transaction.Quantity * transaction.TransactionPrice;
            
            if (investment.Quantity == 0)
            {
                Investments.Remove(transaction.Symbol);
            }
        }
        
            
        
        Save();
    }

    public void Save()
    {
        Directory.CreateDirectory(Dir);
        var json = JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(Filepath, json);
    }

    public static Portfolio Load()
    {
        if (!File.Exists(Filepath))
        {
            return new Portfolio();
        }

        try
        {
            var json = File.ReadAllText(Filepath);
            return JsonSerializer.Deserialize<Portfolio>(json) ?? new Portfolio();
        }
        catch
        {
            return new Portfolio();
        }
    }
    public decimal IndividualPnL(string symbol, decimal currentPrice)
    {
        if (!Investments.TryGetValue(symbol, out var investment))
        {
            return 0;
        }
        decimal pnl = (currentPrice - investment.AverageCost) * investment.Quantity;
        return pnl;
    }

    public decimal ComputePnL(Dictionary<string, decimal> currentPrices)
    {
        if (TotalAssets == 0) return 0;
        decimal pnl = 0;
        foreach (var investment in Investments.Values)
        {
            pnl += IndividualPnL(investment.Symbol, currentPrices.GetValueOrDefault(investment.Symbol, 0));
        }
        decimal pnlPercent = pnl  / TotalAssets * 100;
        return pnlPercent;
    }

    public void Reset()
    {
        RealizedPnL = 0;
        TotalAssets = 0;
        Investments.Clear();
        Save();
    }
}