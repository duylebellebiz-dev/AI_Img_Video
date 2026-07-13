import { useEffect, useRef, useState } from "react";
import { cancelEditBatchJob, createEditBatchJob, getEditBatchJob } from "../api";
import EditJobStatus from "./EditJobStatus";
import ImageDropzone from "./ImageDropzone";
import LogoUploader from "./LogoUploader";
import SizeSelector from "./SizeSelector";
import { AlertIcon, SparklesIcon, Spinner } from "./icons";

const POLL_INTERVAL_MS = 2000;
const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);
const MAX_POLL_ERRORS = 3;

export default function PhotoEditor() {
  const [images, setImages] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [size, setSize] = useState({ width: 1080, height: 1350 });
  const [logoUrl, setLogoUrl] = useState(null);
  const [applyLogo, setApplyLogo] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [job, setJob] = useState(null);
  const pollRef = useRef(null);
  const pollErrorCountRef = useRef(0);

  useEffect(() => {
    return () => clearInterval(pollRef.current);
  }, []);

  function handleLogoChange(url) {
    setLogoUrl(url);
    if (!url) setApplyLogo(false);
    else setApplyLogo(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setNotice(null);

    if (images.length === 0) return setError("Upload at least one photo to edit.");
    if (!prompt.trim()) return setError("Describe how you want the photos edited.");

    setSubmitting(true);
    setJob(null);
    clearInterval(pollRef.current);
    pollErrorCountRef.current = 0;

    try {
      const created = await createEditBatchJob({
        images,
        prompt,
        imageWidth: size.width,
        imageHeight: size.height,
        applyLogo,
      });
      const jobId = created.job_id;

      const poll = async () => {
        try {
          const status = await getEditBatchJob(jobId);
          pollErrorCountRef.current = 0;
          setJob(status);
          if (TERMINAL_STATUSES.has(status.status)) {
            clearInterval(pollRef.current);
          }
        } catch (err) {
          pollErrorCountRef.current += 1;
          if (pollErrorCountRef.current >= MAX_POLL_ERRORS) {
            setError(err.message);
            clearInterval(pollRef.current);
          }
        }
      };

      await poll();
      pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel(jobId) {
    setCancelling(true);
    setError(null);
    try {
      await cancelEditBatchJob(jobId);
      clearInterval(pollRef.current);
      const status = await getEditBatchJob(jobId);
      setJob(status);
      setNotice("Batch photo editing was cancelled.");
    } catch (err) {
      setError(err.message);
    } finally {
      setCancelling(false);
    }
  }

  return (
    <div className="space-y-6">
      <LogoUploader onLogoChange={handleLogoChange} />

      <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm sm:p-8">
        <div>
          <h2 className="text-lg font-semibold text-neutral-900">AI Photo Editor</h2>
          <p className="mt-1 text-sm text-neutral-500">
            Upload one or more photos and describe the edit you want — Claude sharpens the instruction, Gemini
            applies it to every photo.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <ImageDropzone label="Photos" hint="PNG or JPG, upload multiple" multiple files={images} onChange={setImages} />

          <SizeSelector onChange={setSize} />

          <div>
            <label className="block text-sm font-medium text-neutral-900">Edit instruction</label>
            <textarea
              className="mt-1.5 w-full rounded-lg border border-neutral-300 p-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-500/20"
              rows={2}
              placeholder="e.g. change the nail color to a glossy red, keep everything else the same"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </div>

          {logoUrl && (
            <label className="flex items-center gap-2.5 text-sm text-neutral-700">
              <input
                type="checkbox"
                checked={applyLogo}
                onChange={(e) => setApplyLogo(e.target.checked)}
                className="h-4 w-4 rounded border-neutral-300 text-violet-600 focus:ring-violet-500/40"
              />
              Watermark results with the salon logo
            </label>
          )}

          {error && (
            <p className="flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
              {error}
            </p>
          )}
          {notice && <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">{notice}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? (
              <>
                <Spinner className="h-4 w-4 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <SparklesIcon className="h-4 w-4" />
                Edit {images.length > 1 ? `${images.length} Photos` : "Photo"}
              </>
            )}
          </button>
        </form>
      </div>

      <EditJobStatus job={job} cancelling={cancelling} onCancel={handleCancel} />
    </div>
  );
}
