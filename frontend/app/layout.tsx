import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'CEIP - Economic Intelligence Platform',
  description: 'CEMAC Economic Intelligence Platform - Professional Dashboard',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body style={{ margin: 0, fontFamily: 'Inter, system-ui, sans-serif' }}>
        {children}
      </body>
    </html>
  );
}