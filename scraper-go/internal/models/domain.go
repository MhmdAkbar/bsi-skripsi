// scraper-go/internal/models/domain.go
package models

import (
	"time"
)

// Publikasi merepresentasikan artikel berita atau sentimen media sosial
type Publikasi struct {
	ID        uint      `gorm:"primaryKey"`
	Tanggal   time.Time `gorm:"index"`
	Sumber    string    
	Judul     string    
	Konten    string    `gorm:"type:text"`
	Sentimen  float64   
	URL       string    `gorm:"unique"`
	CreatedAt time.Time
}

// KinerjaBulanan merepresentasikan data DEA dan agregasi akhir
type KinerjaBulanan struct {
	Periode          string  `gorm:"primaryKey"` 
	DPK              float64 `gorm:"column:dpk_input"`
	BebanPersonel    float64 `gorm:"column:beban_personel_input"`
	BebanOperasional float64 `gorm:"column:beban_operasional_input"`
	Pembiayaan       float64 `gorm:"column:pembiayaan_output"`
	Pendapatan       float64 `gorm:"column:pendapatan_output"`
	SkorDEA          float64 
	SkorSentimen     float64 
}

type Tweet struct {
	ID      string `gorm:"primaryKey"`
	Content string `gorm:"type:text;index"`
	Date    string 
	Label   string // Untuk hasil IndoBERT nanti
}