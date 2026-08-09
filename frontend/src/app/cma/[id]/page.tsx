import { redirect } from "next/navigation";

export default function CmaIndex({ params }: { params: { id: string } }) {
  redirect(`/cma/${params.id}/subject`);
}
