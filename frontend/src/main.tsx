import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@fontsource-variable/inter";
import "./index.css";
import App from "./App";
import { FiltrosProvider } from "./state";
import { ThemeProvider } from "./theme-context";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <FiltrosProvider>
          <App />
        </FiltrosProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
