import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { ApiError } from "./api/api";
import App from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { pushToast } from "./toast";
import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
import "./styles/tokens.css";
import "./styles/global.css";

const describe = (error: unknown) =>
  error instanceof ApiError ? error.message : error instanceof Error ? error.message : "Something went wrong";
const isAbort = (error: unknown) => error instanceof Error && error.name === "AbortError";

const client = new QueryClient({
  queryCache: new QueryCache({
    // Only toast when there is nothing on screen to show for it; background refetches stay quiet.
    onError: (error, query) => {
      if (!isAbort(error) && query.state.data === undefined && query.meta?.quiet !== true) pushToast(describe(error));
    },
  }),
  mutationCache: new MutationCache({
    onError: (error) => {
      if (!isAbort(error)) pushToast(describe(error));
    },
  }),
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false, staleTime: 5_000 } },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={client}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
);
