package main

import (
	"log"
	"os"

	"github.com/joho/godotenv"
)

var (
	AlpacaKey    string
	AlpacaSecret string
)

func LoadConfig() {
	// Load .env from parent directory
	err := godotenv.Load("../.env")
	if err != nil {
		log.Println("Warning: Error loading .env file, relying on environment variables")
	}

	AlpacaKey = os.Getenv("ALPACA_KEY")
	AlpacaSecret = os.Getenv("ALPACA_SECRET")

	if AlpacaKey == "" || AlpacaSecret == "" {
		log.Println("Warning: ALPACA_KEY or ALPACA_SECRET is missing")
	}
}
