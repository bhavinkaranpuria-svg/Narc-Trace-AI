import "./globals.css";
import Nav from "../components/Nav";

export const metadata = {
  title: "NARC-TRACE AI",
  description: "Intelligent, tamper-evident field drug testing.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="true" />
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="shell">
          <aside className="rail">
            <div className="brand">
              <div className="brand-mark">NARC-TRACE AI</div>
            </div>
            <Nav />
            <div className="rail-foot">
              MODEL cv-pipeline-1.0
              <br />
              MODE local-first
            </div>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
