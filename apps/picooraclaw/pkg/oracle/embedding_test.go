package oracle

import (
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
)

func TestEmbeddingService_New(t *testing.T) {
	db, _, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	svc, err := NewEmbeddingService(db, "ALL_MINILM_L12_V2")
	if err != nil {
		t.Fatalf("NewEmbeddingService failed: %v", err)
	}

	if svc.Dims() != 384 {
		t.Errorf("Dims() = %d, want 384", svc.Dims())
	}
	if svc.ModelName() != "ALL_MINILM_L12_V2" {
		t.Errorf("ModelName() = %q, want %q", svc.ModelName(), "ALL_MINILM_L12_V2")
	}
}

func TestEmbeddingService_EmbedTextEmpty(t *testing.T) {
	db, _, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	svc, err := NewEmbeddingService(db, "ALL_MINILM_L12_V2")
	if err != nil {
		t.Fatalf("NewEmbeddingService failed: %v", err)
	}

	emb, err := svc.EmbedText("")
	if err != nil {
		t.Fatalf("EmbedText('') should not error, got: %v", err)
	}
	if len(emb) != 384 {
		t.Errorf("empty text embedding should be 384-dim zero vector, got %d dims", len(emb))
	}
	for i, v := range emb {
		if v != 0 {
			t.Errorf("emb[%d] = %f, want 0", i, v)
			break
		}
	}
}

func TestEmbeddingService_CheckONNXLoaded(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	svc, err := NewEmbeddingService(db, "ALL_MINILM_L12_V2")
	if err != nil {
		t.Fatalf("NewEmbeddingService failed: %v", err)
	}

	// Model exists
	mock.ExpectQuery("SELECT COUNT").
		WithArgs("ALL_MINILM_L12_V2").
		WillReturnRows(sqlmock.NewRows([]string{"count"}).AddRow(1))

	loaded, err := svc.CheckONNXLoaded()
	if err != nil {
		t.Fatalf("CheckONNXLoaded failed: %v", err)
	}
	if !loaded {
		t.Error("expected model to be loaded")
	}

	// Model not loaded
	mock.ExpectQuery("SELECT COUNT").
		WithArgs("ALL_MINILM_L12_V2").
		WillReturnRows(sqlmock.NewRows([]string{"count"}).AddRow(0))

	loaded, err = svc.CheckONNXLoaded()
	if err != nil {
		t.Fatalf("CheckONNXLoaded failed: %v", err)
	}
	if loaded {
		t.Error("expected model to not be loaded")
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}

func TestEmbeddingService_LoadONNXModel(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("failed to create sqlmock: %v", err)
	}

	svc, err := NewEmbeddingService(db, "TEST_MODEL")
	if err != nil {
		t.Fatalf("NewEmbeddingService failed: %v", err)
	}

	mock.ExpectExec("DBMS_VECTOR.LOAD_ONNX_MODEL").
		WillReturnResult(sqlmock.NewResult(0, 0))

	err = svc.LoadONNXModel("ONNX_DIR", "model.onnx")
	if err != nil {
		t.Fatalf("LoadONNXModel failed: %v", err)
	}

	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("unfulfilled expectations: %v", err)
	}
}
