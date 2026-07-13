const BASE_URL = ""; // same-origin via Vite dev proxy (see vite.config.js)

export async function createBatchJob({
  designImages,
  poseImages,
  pairingMode,
  numImages,
  description,
  imageWidth,
  imageHeight,
}) {
  const form = new FormData();
  designImages.forEach((file) => form.append("design_images", file));
  poseImages.forEach((file) => form.append("pose_images", file));
  form.append("pairing_mode", pairingMode);
  form.append("num_images", String(numImages));
  form.append("description", description);
  if (imageWidth && imageHeight) {
    form.append("image_width", String(imageWidth));
    form.append("image_height", String(imageHeight));
  }

  const res = await fetch(`${BASE_URL}/api/batch`, { method: "POST", body: form });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || "Failed to create batch job");
  }
  return body;
}

export async function getBatchJob(jobId) {
  const res = await fetch(`${BASE_URL}/api/batch/${jobId}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Failed to fetch job status");
  }
  return res.json();
}

export async function cancelBatchJob(jobId) {
  const res = await fetch(`${BASE_URL}/api/batch/${jobId}/cancel`, { method: "POST" });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || "Failed to cancel batch job");
  }
  return body;
}

export function downloadUrl(jobId) {
  return `${BASE_URL}/api/batch/${jobId}/download`;
}

export async function editImage({ image, prompt, imageWidth, imageHeight }) {
  const form = new FormData();
  form.append("image", image);
  form.append("prompt", prompt);
  if (imageWidth && imageHeight) {
    form.append("image_width", String(imageWidth));
    form.append("image_height", String(imageHeight));
  }

  const res = await fetch(`${BASE_URL}/api/edit`, { method: "POST", body: form });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || "Failed to edit image");
  }
  return body;
}

export async function createEditBatchJob({ images, prompt, imageWidth, imageHeight, applyLogo }) {
  const form = new FormData();
  images.forEach((file) => form.append("images", file));
  form.append("prompt", prompt);
  if (imageWidth && imageHeight) {
    form.append("image_width", String(imageWidth));
    form.append("image_height", String(imageHeight));
  }
  form.append("apply_logo", String(Boolean(applyLogo)));

  const res = await fetch(`${BASE_URL}/api/edit/batch`, { method: "POST", body: form });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || "Failed to create edit job");
  }
  return body;
}

export async function getEditBatchJob(jobId) {
  const res = await fetch(`${BASE_URL}/api/edit/batch/${jobId}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Failed to fetch edit job status");
  }
  return res.json();
}

export async function cancelEditBatchJob(jobId) {
  const res = await fetch(`${BASE_URL}/api/edit/batch/${jobId}/cancel`, { method: "POST" });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || "Failed to cancel edit job");
  }
  return body;
}

export function editDownloadUrl(jobId) {
  return `${BASE_URL}/api/edit/batch/${jobId}/download`;
}

export async function getLogo() {
  const res = await fetch(`${BASE_URL}/api/branding/logo`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Failed to fetch salon logo");
  }
  return res.json();
}

export async function uploadLogo(file) {
  const form = new FormData();
  form.append("logo", file);
  const res = await fetch(`${BASE_URL}/api/branding/logo`, { method: "POST", body: form });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || "Failed to upload salon logo");
  }
  return body;
}

export async function deleteLogo() {
  const res = await fetch(`${BASE_URL}/api/branding/logo`, { method: "DELETE" });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || "Failed to remove salon logo");
  }
  return body;
}
