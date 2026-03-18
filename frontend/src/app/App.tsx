import { LazyMotion, domAnimation } from 'framer-motion';
import StudioPage from '@/pages/StudioPage';

/**
 * Root application component.
 * 
 * Provides global context providers and renders the main studio page.
 * LazyMotion reduces bundle size by loading Motion features on demand.
 */
function App() {
  return (
    <LazyMotion features={domAnimation} strict>
      <StudioPage />
    </LazyMotion>
  );
}

export default App;
