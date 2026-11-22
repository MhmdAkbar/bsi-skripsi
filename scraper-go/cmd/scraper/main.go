// scraper-go/cmd/scraper/main.go
package main

import (
	"bsi-scraper/internal/database"
	"bsi-scraper/internal/scraper"
	"log"
)

func main() {
	// Pastikan mengarah ke file db skripsi Anda
	dbConfig := database.Config{
		DSN: "../data/skripsi_bsi.db", 
	}

	db, err := database.InitDB(dbConfig)
	if err != nil {
		log.Fatalf("Fatal Error Koneksi DB: %v", err)
	}
	
	scraperService := scraper.NewService(db)

	log.Println("=== MEMULAI INTEGRASI DATA APIFY ===")
	
	// Masukkan nama file CSV hasil download Apify di sini
	fileName := `F:\skripsi\bsi-skripsi\data\tweets_feb_2021.csv` 
	
	err = scraperService.ImportTweetsFromCSV(fileName)
	if err != nil {
		log.Fatalf("Gagal import: %v", err)
	}

	log.Println("Selesai. Database skripsi_bsi.db telah diperbarui.")
}