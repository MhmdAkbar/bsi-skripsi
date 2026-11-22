// scraper-go/internal/database/sqlite.go
package database

import (
	"fmt"
	"log"

	"bsi-scraper/internal/models"

	"github.com/glebarez/sqlite" // Menggunakan pure-go driver, bebas CGO!
	"gorm.io/gorm"
)

// Config menyimpan konfigurasi database
type Config struct {
	DSN string // Data Source Name (path ke file sqlite)
}

// InitDB menginisialisasi koneksi dan melakukan migrasi
func InitDB(cfg Config) (*gorm.DB, error) {
	// sqlite.Open sekarang memanggil library pure-go glebarez
	db, err := gorm.Open(sqlite.Open(cfg.DSN), &gorm.Config{})
	if err != nil {
		return nil, fmt.Errorf("gagal terhubung ke database: %w", err)
	}

	// Auto-migration model domain
	err = db.AutoMigrate(
		&models.Publikasi{},
		&models.KinerjaBulanan{},
		&models.Tweet{},
	)
	if err != nil {
		return nil, fmt.Errorf("gagal menjalankan migrasi: %w", err)
	}

	log.Println("Database berhasil diinisialisasi dan dimigrasi (Pure Go).")
	return db, nil
}
