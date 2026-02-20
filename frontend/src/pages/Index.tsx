import { useState } from 'react';
import Header from '@/components/Header';
import Hero from '@/components/Hero';
import Experience from '@/components/Experience';
import FitAssessment from '@/components/FitAssessment';
import AIChat from '@/components/AIChat';
import Footer from '@/components/Footer';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { useProfileContext } from '@/context/ProfileContext';

const Index = () => {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const { profile, serviceStatus } = useProfileContext();

  const openChat = () => setIsChatOpen(true);

  // If config.sections is defined, only render those sections; otherwise render all
  const sections = profile?.config?.sections;
  const showSection = (name: string) => !sections || sections.includes(name);

  return (
    <div className="min-h-screen bg-background">
      <ErrorBoundary sectionName="Header">
        <Header onOpenChat={openChat} />
      </ErrorBoundary>
      <main id="main-content">
        {serviceStatus === 'unavailable' && (
          <div className="bg-destructive/10 border-b border-destructive/20 px-4 py-3 text-center text-sm text-destructive">
            Backend service is unavailable. Some features may not work.
          </div>
        )}
        {serviceStatus === 'degraded' && (
          <div className="bg-warning/10 border-b border-warning/20 px-4 py-3 text-center text-sm text-warning">
            Some services are running in degraded mode. AI features may be
            limited.
          </div>
        )}
        {showSection('hero') && (
          <ErrorBoundary sectionName="Hero">
            <Hero onOpenChat={openChat} />
          </ErrorBoundary>
        )}
        {showSection('experience') && (
          <ErrorBoundary sectionName="Experience">
            <Experience />
          </ErrorBoundary>
        )}
        {showSection('fit-assessment') && (
          <ErrorBoundary sectionName="Fit Assessment">
            <FitAssessment />
          </ErrorBoundary>
        )}
      </main>
      <ErrorBoundary sectionName="Footer">
        <Footer />
      </ErrorBoundary>
      <ErrorBoundary sectionName="AI Chat">
        <AIChat isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
      </ErrorBoundary>
    </div>
  );
};

export default Index;
