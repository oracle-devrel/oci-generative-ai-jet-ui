import {
  Box,
  Button,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useState, useContext } from "react";
import { useForm } from "react-hook-form";
import IdentityContext from "./IdentityContext";

function SummaryText() {
  const identity = useContext(IdentityContext);
  const { register, handleSubmit, reset } = useForm();
  const [waiting, setWaiting] = useState(false);
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState();
  const [summary, setSummary] = useState("");

  const onSubmit = async (data) => {
    setWaiting(true);
    const body = JSON.stringify({
      content: data.fullText,
    });

    const res = await fetch("/api/genai/summary", {
      method: "POST",
      body: body,
      headers: {
        "Content-Type": "application/json",
        conversationId: identity,
        modelId: "n/a",
      },
    });
    const responseData = await res.json();
    const { content, errorMessage } = responseData;
    if (errorMessage.length) {
      setErrorMessage(errorMessage);
      setShowError(true);
    } else {
      setSummary(content);
    }
    setWaiting(false);
    reset();
  };
  return (
    <Box>
      <form onSubmit={handleSubmit(onSubmit)}>
        <Stack alignItems={"center"}>
          <TextField
            multiline
            maxRows={10}
            style={{ width: "30rem" }}
            {...register("fullText")}
          />
          <Button disabled={waiting} type="submit">
            Submit
          </Button>
        </Stack>
      </form>
      {summary.length !== 0 && <Typography>{summary}</Typography>}
      <Snackbar
        open={showError}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        autoHideDuration={6000}
        onClose={() => {
          setErrorMessage();
          setShowError(false);
        }}
        message={errorMessage}
      />
    </Box>
  );
}

export default SummaryText;
