import type { LabelData, LabelImage } from "../api/api";
import styles from "../pages/LabelPage.module.css";

export const fileStem = (label: LabelData) => `${label.artist} - ${label.title}`.replace(/[\\/:*?"<>|]/g, "");

function download(image: LabelImage, stem: string) {
  const link = document.createElement("a");
  link.href = `data:image/png;base64,${image.png_base64}`;
  link.download = `${stem} (${image.name}).png`;
  link.click();
}

const imageTitle = (image: LabelImage) =>
  image.kind === "main" ? "Main label" : image.name === "tracks" ? "Tracks label" : `Tracks label ${image.name.split("-")[1]}`;

type Props = { images: LabelImage[]; warnings: string[]; stem: string; onReset: () => void; canReset: boolean; hint: string };

export function LabelPreview({ images, warnings, stem, onReset, canReset, hint }: Props) {
  const downloadAll = () => images.forEach((image, i) => setTimeout(() => download(image, stem), i * 250));
  return (
    <aside className={styles.preview} aria-label="Preview">
      <div className={styles.actions}>
        <button className="primary" onClick={downloadAll} disabled={images.length === 0}>
          Download {images.length > 1 ? `${images.length} labels` : "label"} (PNG)
        </button>
        <button className="ghost" onClick={onReset} disabled={!canReset}>Reset edits</button>
      </div>
      {warnings.length > 0 && (
        <ul className={styles.warnings} aria-label="Warnings">
          {warnings.map((w) => <li key={w}>{w}</li>)}
        </ul>
      )}
      {images.map((image) => (
        <figure key={image.name} className={styles.figure}>
          <img src={`data:image/png;base64,${image.png_base64}`} alt={`${imageTitle(image)} preview`} width={image.width} height={image.height} />
          <figcaption>
            <span className="micro">{imageTitle(image)} · 62 × 40 mm</span>
            <button className="ghost small" onClick={() => download(image, stem)}>Download</button>
          </figcaption>
        </figure>
      ))}
      <p className={styles.hint}>{hint}</p>
    </aside>
  );
}
