# Stock Trader App

A simple stock trading/demo app with an ASP.NET Core (C#) backend and a React frontend.

![UI](misc/UI.png)

## Features
- Real-time market data and quotes
- View/search stocks, view details and charts
- Simulated buy/sell and portfolio management
- Lightweight REST API used by React frontend

## Tech stack
- Backend: .NET 7 / ASP.NET Core Web API (C#)
- Frontend: React (Vite or Create React App) + TypeScript (optional)
- Data: In-memory or SQLite for demo; optional external market API
- Optional: SignalR for real-time updates

## Repository layout (suggested)
- /src/Server — ASP.NET Core Web API (C#)
- /src/Client — React app
- /misc/UI.png — UI screenshot (included)

## Prerequisites
- .NET 7 SDK
- Node.js 18+
- npm or yarn

## Quick start

Backend
```
cd src/Server
dotnet restore
dotnet run --urls http://localhost:5000
```

Frontend
```
cd src/Client
npm install
npm start   # opens http://localhost:3000
```

Configure the client API base URL if needed (e.g., REACT_APP_API_URL=http://localhost:5000).

## Environment / config
- SERVER_PORT (backend port)
- DATABASE_URL (optional SQLite file path)
- MARKET_API_KEY (optional external market data provider)

## API (examples)
- GET /api/stocks?query={symbol|name} — search/list quotes
- GET /api/stocks/{symbol} — stock details
- POST /api/orders — place buy/sell (body: symbol, quantity, side)
- GET /api/portfolio — user portfolio and positions

Authentication is optional for demo; adapt endpoints to use JWT if required.

## Development notes
- Keep business logic in Server/Services and minimal controller code.
- Frontend: use fetch/axios to call /api; keep UI state in context or Redux.
- Add SignalR hub for push updates if implementing live prices.

## Contributing
Fork, create a feature branch, open a PR with concise description and tests.

## License
MIT — adapt as needed.
