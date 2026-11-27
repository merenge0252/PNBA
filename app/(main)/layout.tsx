import Link from "next/link";
import { logout } from "../actions";

export default function MainLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <header className="bar">
        <Link className="brand" href="/">
          PNBA
        </Link>
        <nav>
          <Link href="/">今日</Link>
          <Link href="/archive">過去</Link>
          <Link href="/settings">設定</Link>
          <form action={logout} className="inline">
            <button className="link">ログアウト</button>
          </form>
        </nav>
      </header>
      <main>{children}</main>
    </>
  );
}
