const DEFAULT_MAX_ROWS = 200_000;
const DEFAULT_MAX_BYTES = 150 * 1024 * 1024;
const DEFAULT_CHUNK_BYTES = 1024 * 1024;

export interface SampleCsvOptions {
  maxRows?: number;
  maxBytes?: number;
}

export async function sampleCsvFirstRows(file: File, opts: SampleCsvOptions = {}): Promise<File> {
  const maxRows = opts.maxRows ?? DEFAULT_MAX_ROWS;
  const maxBytes = opts.maxBytes ?? DEFAULT_MAX_BYTES;

  const decoder = new TextDecoder("utf-8", { fatal: false });
  const reader = file.stream().getReader();

  let header: string | null = null;
  let outputParts: string[] = [];
  let leftover = "";
  let rowsCollected = 0;
  let outputBytes = 0;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    const chunkText = decoder.decode(value, { stream: true });
    let text = leftover + chunkText;

    let newlineIdx: number;
    while ((newlineIdx = text.indexOf("\n")) !== -1) {
      const line = text.slice(0, newlineIdx + 1);
      text = text.slice(newlineIdx + 1);

      if (header === null) {
        header = line;
        outputParts.push(header);
        outputBytes += new Blob([header]).size;
        continue;
      }

      if (rowsCollected >= maxRows) {
        await reader.cancel();
        break;
      }

      const lineBytes = new Blob([line]).size;
      if (outputBytes + lineBytes > maxBytes) {
        await reader.cancel();
        break;
      }

      outputParts.push(line);
      outputBytes += lineBytes;
      rowsCollected += 1;
    }

    if (rowsCollected >= maxRows || outputBytes >= maxBytes) {
      break;
    }

    leftover = text;
  }

  if (header === null) {
    return file;
  }

  const sampledBlob = new Blob(outputParts, { type: "text/csv" });
  const baseName = file.name.toLowerCase().endsWith(".csv") ? file.name.slice(0, -4) : file.name;
  const sampledName = `${baseName}.sampled.csv`;

  return new File([sampledBlob], sampledName, {
    type: "text/csv",
    lastModified: Date.now(),
  });
}

export function shouldSampleBeforeUpload(file: File): boolean {
  return file.size > DEFAULT_MAX_BYTES;
}
