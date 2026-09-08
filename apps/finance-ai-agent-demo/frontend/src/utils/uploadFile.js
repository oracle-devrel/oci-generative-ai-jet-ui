export async function uploadFile(file, threadId, dispatch) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("thread_id", threadId);
  try {
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (res.ok) {
      dispatch({
        type: "ADD_SYSTEM_MESSAGE",
        payload: `Uploaded ${data.filename} - ${data.chunks_created} chunks indexed.`,
      });
    } else {
      dispatch({
        type: "ADD_SYSTEM_MESSAGE",
        payload: `Upload failed: ${data.error || "Unknown error"}`,
      });
    }
  } catch {
    dispatch({ type: "ADD_SYSTEM_MESSAGE", payload: "Upload failed: network error" });
  }
}
