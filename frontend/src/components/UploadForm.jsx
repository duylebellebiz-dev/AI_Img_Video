import { useEffect, useState } from "react";
import ImageDropzone from "./ImageDropzone";
import SizeSelector from "./SizeSelector";
import { SparklesIcon, Spinner } from "./icons";

const PAIRING_MODES = [
  { value: "cross", label: "Cross Pair", help: "Every design × every pose combination." },
  { value: "random", label: "Random Pair", help: "Randomly pairs designs with poses." },
  { value: "one_to_one", label: "One-to-One", help: "Pairs each design with one pose, in order." },
];

function getOutputPreview(designCount, poseCount, pairingMode, requestedCount) {
  if (designCount < 1 || poseCount < 1 || !Number.isInteger(requestedCount) || requestedCount < 1) {
    return null;
  }

  const basePairs = Math.min(designCount, poseCount);
  const safeLimit = basePairs * 2;
  const extendedLimit = Math.min(designCount * poseCount, basePairs * 3);
  const hardLimit = designCount * poseCount;

  const modeLimit =
    pairingMode === "one_to_one" ? safeLimit : pairingMode === "random" ? extendedLimit : hardLimit;
  const approvedCount = Math.min(requestedCount, modeLimit, 100);

  return { approvedCount, modeLimit };
}

export default function UploadForm({ onSubmit, submitting }) {
  const [designImages, setDesignImages] = useState([]);
  const [poseImages, setPoseImages] = useState([]);
  const [pairingMode, setPairingMode] = useState("cross");
  const [numImages, setNumImages] = useState(20);
  const [description, setDescription] = useState("summer luxury nail design");
  const [size, setSize] = useState({ width: 1080, height: 1350 });
  const [error, setError] = useState(null);
  const outputPreview = getOutputPreview(designImages.length, poseImages.length, pairingMode, numImages);
  const activeMode = PAIRING_MODES.find((m) => m.value === pairingMode);

  useEffect(() => {
    if (outputPreview && numImages > outputPreview.modeLimit) {
      setNumImages(outputPreview.modeLimit);
    }
  }, [numImages, outputPreview]);

  function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (designImages.length === 0) return setError("Upload at least one nail design image.");
    if (poseImages.length === 0) return setError("Upload at least one hand pose image.");
    if (!Number.isInteger(numImages) || numImages < 1 || numImages > 100) {
      return setError("Number of images must be an integer between 1 and 100.");
    }
    if (outputPreview && numImages > outputPreview.modeLimit) {
      return setError(`This input set supports up to ${outputPreview.modeLimit} image(s) in ${pairingMode} mode.`);
    }

    onSubmit({
      designImages,
      poseImages,
      pairingMode,
      numImages,
      description,
      imageWidth: size.width,
      imageHeight: size.height,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm sm:p-8">
      <div>
        <h2 className="text-lg font-semibold text-neutral-900">Batch Image Generator</h2>
        <p className="mt-1 text-sm text-neutral-500">
          Upload nail designs + hand poses and generate a full campaign of on-brand product photos in one go.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-neutral-900">Campaign description</label>
        <textarea
          className="mt-1.5 w-full rounded-lg border border-neutral-300 p-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-500/20"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="e.g. summer luxury nail design"
        />
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <ImageDropzone
          label={`Nail design images (${designImages.length})`}
          hint="PNG or JPG, one or more"
          multiple
          files={designImages}
          onChange={setDesignImages}
        />
        <ImageDropzone
          label={`Hand pose images (${poseImages.length})`}
          hint="PNG or JPG, one or more"
          multiple
          files={poseImages}
          onChange={setPoseImages}
        />
      </div>

      <SizeSelector onChange={setSize} />

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-neutral-900">Pairing mode</label>
          <select
            className="mt-1.5 w-full rounded-lg border border-neutral-300 px-3 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-500/20"
            value={pairingMode}
            onChange={(e) => setPairingMode(e.target.value)}
          >
            {PAIRING_MODES.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
          {activeMode && <p className="mt-1.5 text-xs text-neutral-500">{activeMode.help}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-neutral-900">Number of images (1-100)</label>
          <input
            type="number"
            min={1}
            max={outputPreview?.modeLimit ?? 100}
            className="mt-1.5 w-full rounded-lg border border-neutral-300 px-3 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-500/20"
            value={numImages}
            onChange={(e) => {
              const nextValue = parseInt(e.target.value, 10);
              if (Number.isNaN(nextValue)) {
                setNumImages(1);
                return;
              }
              setNumImages(outputPreview ? Math.min(nextValue, outputPreview.modeLimit) : nextValue);
            }}
          />
          {outputPreview && (
            <p className="mt-1.5 text-xs text-neutral-500">
              Up to {outputPreview.modeLimit} image(s) possible with this input in {pairingMode} mode.
            </p>
          )}
        </div>
      </div>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? (
          <>
            <Spinner className="h-4 w-4 animate-spin" />
            Starting batch...
          </>
        ) : (
          <>
            <SparklesIcon className="h-4 w-4" />
            Generate Batch
          </>
        )}
      </button>
    </form>
  );
}
