import type { Metadata } from "next";
import { Suspense } from "react";

import { SectionHeading } from "@/components/ui/card";
import { ReportForm } from "@/features/community/report-form";

export const metadata: Metadata = { title: "Report a scam" };

export default function ReportPage() {
  return (
    <div className="space-y-8">
      <SectionHeading
        as="h1"
        eyebrow="Report scam"
        title="Report a scam"
        description="Help warn others. Reports are anonymous and appear on the scam map only as a city and category."
      />
      <Suspense fallback={<div className="h-96 animate-pulse rounded-md border border-line bg-surface" />}>
        <ReportForm />
      </Suspense>
    </div>
  );
}
