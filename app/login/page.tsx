import { redirect } from "next/navigation";
import LoginForm from "@/components/LoginForm";
import { config } from "@/lib/env";
import { isLoggedIn } from "@/lib/session";

export const metadata = { title: "ログイン - PNBA" };

export default async function LoginPage() {
  if (await isLoggedIn()) redirect("/");
  return (
    <main>
      <LoginForm configured={Boolean(config.password)} />
    </main>
  );
}
