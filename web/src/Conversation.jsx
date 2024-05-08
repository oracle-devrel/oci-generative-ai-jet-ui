import { Avatar, Box, Paper, Stack, Typography } from "@mui/material";
import { deepOrange, deepPurple } from "@mui/material/colors";

function Conversation({ children: conversation }) {
  if (!conversation.length) return;
  return (
    <Paper elevation={0} style={{ padding: "1rem", marginBottom: "1rem" }}>
      <Stack spacing={1} direction={"column"}>
        {conversation.map(({ id, user, content }) => {
          return (
            <Stack
              direction={"row"}
              sx={{
                alignItems: "center",
                justifyContent: user === "ai" ? "left" : "right",
              }}
              spacing={1}
              key={id}
            >
              {user === "ai" && <AIAvatar />}
              <Typography>{content}</Typography>
              {user !== "ai" && <MeAvatar />}
            </Stack>
          );
        })}
      </Stack>
    </Paper>
  );
}

function AIAvatar() {
  return <Avatar sx={{ bgcolor: deepOrange[500] }}>AI</Avatar>;
}

function MeAvatar() {
  return <Avatar sx={{ bgcolor: deepPurple[500] }}>Me</Avatar>;
}

export default Conversation;
