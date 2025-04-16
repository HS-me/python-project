import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '회식 주기 투표 시스템',
  description: '회식 주기에 대한 투표를 진행하는 시스템입니다.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>
        <div className="container">
          {children}
        </div>
      </body>
    </html>
  );
} 