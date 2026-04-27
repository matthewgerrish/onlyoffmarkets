import { Helmet } from 'react-helmet-async';

export default function Seo({ title, description }: { title: string; description?: string }) {
  const full = `${title} · OnlyOffMarkets`;
  return (
    <Helmet>
      <title>{full}</title>
      {description && <meta name="description" content={description} />}
      <meta property="og:title" content={full} />
      {description && <meta property="og:description" content={description} />}
    </Helmet>
  );
}
