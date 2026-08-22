import { useRef, useState } from "react";

const ACCEPT = ".mp4,.mov,.mkv,.webm,.avi,video/*";

export default function VideoUploader({ file, onFileChange, disabled, error }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  function handleFiles(fileList) {
    const next = fileList?.[0];
    if (next) onFileChange(next);
  }

  return (
    <div className="flex h-full flex-col justify-between p-4">
      <div>
        <div className="label-micro mb-2">Video</div>
        <div
          onClick={() => !disabled && inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            if (!disabled) setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (!disabled) handleFiles(e.dataTransfer.files);
          }}
          className={`rounded-[3px] border border-dashed px-3 py-2.5 text-[11px] font-mono text-ink/80 transition-colors ${
            disabled
              ? "opacity-50 border-line"
              : `cursor-pointer hover:border-ink/40 ${dragOver ? "border-node-blue bg-node-blue/5" : "border-line"}`
          }`}
        >
          {file ? (
            <span className="truncate">{file.name}</span>
          ) : (
            <span className="text-muted">click or drop an MP4/MOV/MKV/WEBM/AVI</span>
          )}
          {file && <span className="text-muted"> — click or drop to replace</span>}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          disabled={disabled}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
      {error ? (
        <p className="mt-3 text-[10.5px] leading-snug text-thread-red">{error}</p>
      ) : (
        <p className="mt-3 text-[10.5px] leading-snug text-muted">
          Runs through the real video→transcript→persona pipeline on Run. Max 100MB.
        </p>
      )}
    </div>
  );
}
