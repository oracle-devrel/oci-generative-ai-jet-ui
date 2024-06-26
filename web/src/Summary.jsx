import {
  Box,
  Button,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useStomp } from "./stompHook";

function Summary() {
  const { register, handleSubmit } = useForm();
  const [waiting, setWaiting] = useState(false);
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState();
  const [summary, setSummary] = useState("");
  const { subscribe, unsubscribe, isConnected } = useStomp();

  useEffect(() => {
    if (isConnected) {
      subscribe("/user/queue/summary", (message) => {
        setWaiting(false);
        if (message.errorMessage.length > 0) {
          setErrorMessage(message.errorMessage);
          setShowError(true);
        } else {
          console.log("/user/queue/summary");
          console.log(message);
          setSummary(message);
        }
      });
    }

    return () => {
      unsubscribe("/user/queue/summary");
    };
  }, [isConnected]);

  const onSubmit = async (data) => {
    const formData = new FormData();
    formData.append("file", data.file[0]);

    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });
    const responseData = await res.json();
    const { content, errorMessage } = responseData;
    if (errorMessage.length) {
      setErrorMessage(errorMessage);
      setShowError(true);
    } else {
      console.log(content);
      setSummary(content);
    }
  };
  return (
    <Box>
      <form onSubmit={handleSubmit(onSubmit)}>
        <Stack alignItems={"center"}>
          <TextField
            style={{ width: "30rem" }}
            type="file"
            {...register("file")}
          />

          <Button type="submit">Submit</Button>
        </Stack>
      </form>
      {summary.length && <Typography>{summary}</Typography>}
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

export default Summary;
