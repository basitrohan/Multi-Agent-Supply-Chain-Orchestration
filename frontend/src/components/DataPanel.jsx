import { useRef, useState } from "react";
import Card from "./Card";
import { api, ApiError } from "../lib/api";

export default function DataPanel({ summary, onDataChanged }) {
  const [uploadState, setUploadState] = useState({}); // { suppliers: {...}, inventory: {...} }
  const supplierInputRef = useRef(null);
  const inventoryInputRef = useRef(null);

  async function handleUpload(entityType, file) {
    if (!file) return;
    setUploadState((s) => ({ ...s, [entityType]: { status: "uploading" } }));
    try {
      const result = await api.uploadCsv(entityType, file);
      setUploadState((s) => ({
        ...s,
        [entityType]: { status: "success", message: result.message },
      }));
      onDataChanged();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Upload failed.";
      setUploadState((s) => ({ ...s, [entityType]: { status: "error", message } }));
    }
  }

  return (
    <Card className="data-card">
      <h2 className="card-heading">Data source</h2>
      <p className="card-subhead">
        The pipeline runs against this supplier and inventory data. Replace it with
        your own CSV at any time.
      </p>

      <div className="data-counts">
        <div className="data-count">
          <span className="data-count-number mono">{summary?.supplier_count ?? "—"}</span>
          <span className="data-count-label">Suppliers</span>
        </div>
        <div className="data-count">
          <span className="data-count-number mono">{summary?.inventory_count ?? "—"}</span>
          <span className="data-count-label">SKUs</span>
        </div>
        <div className="data-count">
          <span className="data-count-number mono">{summary?.regions?.length ?? "—"}</span>
          <span className="data-count-label">Regions</span>
        </div>
      </div>

      {summary?.regions?.length > 0 && (
        <div className="data-regions">
          {summary.regions.map((r) => (
            <span key={r} className="region-pill">
              {r}
            </span>
          ))}
        </div>
      )}

      <div className="upload-row">
        <UploadSlot
          label="Suppliers CSV"
          inputRef={supplierInputRef}
          state={uploadState.suppliers}
          onFile={(file) => handleUpload("suppliers", file)}
        />
        <UploadSlot
          label="Inventory CSV"
          inputRef={inventoryInputRef}
          state={uploadState.inventory}
          onFile={(file) => handleUpload("inventory", file)}
        />
      </div>
    </Card>
  );
}

function UploadSlot({ label, inputRef, state, onFile }) {
  return (
    <div className="upload-slot">
      <span className="field-label">{label}</span>
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        onChange={(e) => onFile(e.target.files?.[0])}
        className="upload-input"
      />
      {state?.status === "uploading" && <span className="upload-note">Uploading…</span>}
      {state?.status === "success" && (
        <span className="upload-note upload-note-ok">{state.message}</span>
      )}
      {state?.status === "error" && (
        <span className="upload-note upload-note-error">{state.message}</span>
      )}
    </div>
  );
}
