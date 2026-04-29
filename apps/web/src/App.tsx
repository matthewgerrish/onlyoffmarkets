import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import ScrollToTop from './components/ScrollToTop';
import Landing from './pages/Landing';
import Search from './pages/Search';
import Property from './pages/Property';
import Sources from './pages/Sources';
import Alerts from './pages/Alerts';
import Pricing from './pages/Pricing';
import About from './pages/About';
import Mailers from './pages/Mailers';
import MailerEditor from './pages/MailerEditor';
import Tokens from './pages/Tokens';
import NotFound from './pages/NotFound';

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Landing />} />
          <Route path="search" element={<Search />} />
          <Route path="property/:id" element={<Property />} />
          <Route path="sources" element={<Sources />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="mailers" element={<Mailers />} />
          <Route path="mailers/new" element={<MailerEditor />} />
          <Route path="tokens" element={<Tokens />} />
          <Route path="pricing" element={<Pricing />} />
          <Route path="about" element={<About />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </>
  );
}
