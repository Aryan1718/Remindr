import ReactDOM from "react-dom/client";
import { AppProviders } from "@/app/providers";
import { AppRouter } from "@/app/router";
import { OceanCursor } from "@/components/ui/OceanCursor";
import "@/styles/tokens.css";
import "@/styles/globals.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <AppProviders>
    <div className="remindr-ocean-cursor-scope">
      <OceanCursor />
      <AppRouter />
    </div>
  </AppProviders>,
);
