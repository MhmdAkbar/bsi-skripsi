// scraper-go/internal/scraper/service.go
package scraper

import (
	"bsi-scraper/internal/models"
	"bufio"
	"fmt"
	"log"
	"os"
	"strings"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

// Service wraps the database dependency for scraper operations.
type Service struct {
	DB *gorm.DB
}

// NewService initializes and returns a new Service instance.
func NewService(db *gorm.DB) *Service {
	return &Service{DB: db}
}

// ImportTweetsFromCSV processes and imports tweet data from a CSV file into the database.
func (s *Service) ImportTweetsFromCSV(filePath string) error {
	f, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("gagal buka file: %v", err)
	}
	defer f.Close()

	fi, _ := f.Stat()
	log.Printf("File OK! Ukuran: %d bytes", fi.Size())

	scanner := bufio.NewScanner(f)

	// Increase buffer capacity to handle exceptionally long lines.
	const maxCapacity = 1024 * 1024
	buf := make([]byte, maxCapacity)
	scanner.Buffer(buf, maxCapacity)

	// Skip the header row.
	if !scanner.Scan() {
		return fmt.Errorf("file kosong atau tidak bisa baca header")
	}

	var totalProcessed, newSaved, duplicateID, duplicateContent int
	log.Println("Memulai Import Mode Brutal (Line-by-Line)...")

	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}

		// Filter out non-Indonesian content to maintain dataset relevance.
		if !strings.Contains(strings.ToLower(line), "\"in\"") {
			continue
		}

		// Split the line using quote-comma-quote as the primary delimiter.
		columns := strings.Split(line, "\",\"")

		// Fallback to standard comma delimiter if the primary split fails.
		if len(columns) < 3 {
			columns = strings.Split(line, ",")
		}

		// Ensure the minimum required columns are present.
		if len(columns) < 4 {
			continue
		}

		totalProcessed++

		// Sanitize the extracted columns by removing bounding quotes and spaces.
		tweetID := strings.Trim(columns[0], "\" ")
		content := strings.Trim(columns[2], "\" ")
		dateRaw := strings.Trim(columns[3], "\" ")

		if tweetID == "" || content == "" {
			continue
		}

		// Prevent insertion of duplicated content.
		var count int64
		s.DB.Model(&models.Tweet{}).Where("content = ?", content).Count(&count)
		if count > 0 {
			duplicateContent++
			continue
		}

		// Map data to the model.
		tweet := models.Tweet{
			ID:      tweetID,
			Content: content,
			Date:    dateRaw,
		}

		// Execute database insertion while ignoring primary key conflicts.
		result := s.DB.Clauses(clause.OnConflict{DoNothing: true}).Create(&tweet)

		if result.RowsAffected > 0 {
			newSaved++
		} else {
			duplicateID++
		}

		if totalProcessed%1000 == 0 {
			log.Printf("Processing... %d baris terlampaui", totalProcessed)
		}
	}

	if err := scanner.Err(); err != nil {
		log.Printf("Error saat scanning file: %v", err)
	}

	fmt.Println("\n--- FINAL REPORT (MODE BRUTAL) ---")
	fmt.Printf("Baris Berhasil Diproses : %d\n", totalProcessed)
	fmt.Printf("Data Unik Baru Masuk    : %d\n", newSaved)
	fmt.Printf("Duplikat ID (Skip)      : %d\n", duplicateID)
	fmt.Printf("Duplikat Isi (Skip)     : %d\n", duplicateContent)
	fmt.Println("--------------------")

	return nil
}

// ScrapeArtikel retrieves and stores article data from the specified URL.
func (s *Service) ScrapeArtikel(urlTarget string) { /* ... */ }
