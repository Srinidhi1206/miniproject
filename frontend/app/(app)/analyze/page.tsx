import type { Metadata } from "next";

import { SectionHeading } from "@/components/ui/card";
import { AnalyzeWorkspace } from "@/features/scanner/analyze-workspace";

export const metadata: Metadata = { title: "Analyze" };

export default function AnalyzePage() {
  return (
    <div className="space-y-8">
      <SectionHeading
        as="h1"
        eyebrow="Analyze"
        title="Check something suspicious"
        description="Messages, links, screenshots and QR codes. SENTINEL shows each step of its analysis as it runs."
      />
      <AnalyzeWorkspace />
    </div>
  );
}
