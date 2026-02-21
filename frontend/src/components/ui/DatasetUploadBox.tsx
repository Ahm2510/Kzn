import { cn } from "@/lib/utils";
import { Upload, FileSpreadsheet, X } from "lucide-react";
import { useState, useRef } from "react";

interface DatasetUploadBoxProps {
  label: string;
  description?: string;
  isOptional?: boolean;
  onFileSelect?: (file: File) => void;
  className?: string;
}

export function DatasetUploadBox({
  label,
  description,
  isOptional = false,
  onFileSelect,
  className,
}: DatasetUploadBoxProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (selectedFile: File) => {
    setFile(selectedFile);
    onFileSelect?.(selectedFile);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.name.endsWith('.csv')) {
      handleFile(droppedFile);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const clearFile = () => {
    setFile(null);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-baseline gap-2">
        <label className="text-sm font-medium text-foreground">
          {label}
        </label>
        {isOptional && (
          <span className="text-xs text-muted-foreground">(optional)</span>
        )}
      </div>
      {description && (
        <p className="text-sm text-muted-foreground">{description}</p>
      )}
      
      {file ? (
        <div className="group flex items-center gap-3 bg-card border border-border rounded-lg p-4 transition-all duration-200 hover:border-primary/30 hover:shadow-sm">
          <FileSpreadsheet className="w-5 h-5 text-primary flex-shrink-0 transition-transform duration-200 group-hover:scale-110" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate transition-colors duration-200 group-hover:text-primary">{file.name}</p>
            <p className="text-xs text-muted-foreground font-mono">
              {(file.size / 1024).toFixed(1)} KB
            </p>
          </div>
          <button
            onClick={clearFile}
            className="p-1.5 hover:bg-destructive/10 rounded transition-all duration-200 hover:scale-110 active:scale-95"
          >
            <X className="w-4 h-4 text-muted-foreground hover:text-destructive transition-colors duration-200" />
          </button>
        </div>
      ) : (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => inputRef.current?.click()}
          className={cn(
            "group border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-all duration-200 ease-out",
            isDragging 
              ? "border-primary bg-primary/5 scale-[1.02]" 
              : "border-border hover:border-primary/40 hover:bg-card hover:shadow-inner"
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => {
              const selectedFile = e.target.files?.[0];
              if (selectedFile) handleFile(selectedFile);
            }}
          />
          <Upload className={cn(
            "w-10 h-10 text-muted-foreground mx-auto mb-4 transition-all duration-200",
            "group-hover:text-primary group-hover:scale-110 group-hover:-translate-y-1",
            isDragging && "text-primary scale-110 -translate-y-1 animate-bounce"
          )} />
          <p className="text-muted-foreground transition-colors duration-200 group-hover:text-foreground">
            Drop CSV file or <span className="text-primary font-medium">browse</span>
          </p>
        </div>
      )}
    </div>
  );
}
