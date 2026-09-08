import { Layout } from "./components/Layout";
import { ThemeProvider } from "./theme";

export default function App() {
  return (
    <ThemeProvider>
      <Layout />
    </ThemeProvider>
  );
}
