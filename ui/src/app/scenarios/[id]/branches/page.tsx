"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";

// Placeholder; the branch/diff view (B5.6) enriches this route.
export default function BranchesPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Branches</h1>
        <Button asChild variant="outline">
          <Link href={`/scenarios/${id}`}>Back</Link>
        </Button>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm text-neutral-500">
            Branch comparison + diff chega no B5.6.
          </CardTitle>
        </CardHeader>
      </Card>
    </div>
  );
}
