#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Trade Application...${NC}\n"

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${RED}Shutting down services...${NC}"
    kill $(jobs -p) 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Start backend (.NET)
echo -e "${GREEN}Starting Backend (ASP.NET Core)...${NC}"
cd app
dotnet run --launch-profile http &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to initialize
sleep 2

# Start frontend (Vite)
echo -e "${GREEN}Starting Frontend (React + Vite)...${NC}"
cd client
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Backend running on http://localhost:5077${NC}"
echo -e "${GREEN}✓ Frontend running on http://localhost:5173${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "\nPress ${RED}Ctrl+C${NC} to stop both services\n"

# Wait for both processes
wait

# Made with Bob
