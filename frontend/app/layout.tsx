import type { Metadata } from "next";
import { Fraunces, Manrope } from "next/font/google";
import { GlobalLoadingIndicator } from "@/components/global-loading-indicator";
import { ToastContainer } from "@/components/toast";
import { Providers } from "@/lib/providers";
import "./globals.css";

const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope" });
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces" });

export const metadata: Metadata = {
  title: "Skyreon Workforce Portal",
  description: "Projects, time, leave and holidays for Skyreon teams",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${manrope.variable} ${fraunces.variable} font-sans antialiased`}>
        <Providers>
          <GlobalLoadingIndicator />
          <ToastContainer />
          {children}
        </Providers>
      </body>
    </html>
  );
}
