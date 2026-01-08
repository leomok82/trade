using Alpaca.Markets;
using Microsoft.AspNetCore.DataProtection;
using System;
using System.IO;
using System.Text;
using System.Text.Json;

internal record Credentials(string Key, string Secret);


public class CredentialProvider
{
    private readonly object _lock = new();
    private IAlpacaDataClient? _dataClient;
    private string? _cachedKey;
    private string? _cachedSecret;
    private readonly SecretStore _secretStore;

    public CredentialProvider(SecretStore secretStore)
    {
        _secretStore = secretStore;
    }

    public (string key, string secret)? Get()
    {
        var creds = _secretStore.Load(); // adjust if this returns null or throws

        if (creds == null) return null;

        var (key, secret) = creds.Value;

        if (string.IsNullOrWhiteSpace(key) || string.IsNullOrWhiteSpace(secret))
            return null;

        return (key, secret);
    }

    public IAlpacaDataClient? GetOrCreateClient()
    {
        var creds = Get();
        if (creds == null) return null;

        var (key, secret) = creds.Value;

        lock (_lock)
        {
            // reuse if unchanged
            if (_dataClient != null && _cachedKey == key && _cachedSecret == secret)
                return _dataClient;

            _cachedKey = key;
            _cachedSecret = secret;

            var credentials = new SecretKey(key, secret);
            _dataClient = Alpaca.Markets.Environments.Live.GetAlpacaDataClient(credentials);

            return _dataClient;
        }
    }

    public void Invalidate()
    {
        lock (_lock)
        {
            _dataClient = null;
            _cachedKey = null;
            _cachedSecret = null;
        }
    }
}

public class SecretStore
{
    private readonly IDataProtector _protector;
    private static readonly string Dir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "bin"
    );

    private static readonly string Filepath = Path.Combine(Dir, "secrets.bin");

    public SecretStore(IDataProtectionProvider protectionProvider)
    {
        _protector = protectionProvider.CreateProtector("AlpacaKeys");
    }

    public void Save(string secret, string key)
    {
        Directory.CreateDirectory(Dir);

        var creds = new Credentials(key.Trim(), secret.Trim());
        var json =  JsonSerializer.Serialize(creds);
        byte[] plainBytes = Encoding.UTF8.GetBytes(json);
        byte[] encryptedBytes = _protector.Protect(plainBytes);
        File.WriteAllBytes(Filepath, encryptedBytes);
    }

    public (string, string)? Load()
    { 
        if (!File.Exists(Filepath))
        {
            // Return null instead of throwing to be safe
            return null;
        }

        try 
        {
            byte[] encryptedBytes = File.ReadAllBytes(Filepath);
            byte[] plainBytes = _protector.Unprotect(encryptedBytes);
            var json = Encoding.UTF8.GetString(plainBytes);
            var creds = JsonSerializer.Deserialize<Credentials>(json);
            if (creds == null) return null;
            return (creds.Key, creds.Secret);
        } 
        catch 
        {
            return null;
        }
    }

    public void Delete()
    {
        if (File.Exists(Filepath))
        {
            File.Delete(Filepath);
        }
    }
}