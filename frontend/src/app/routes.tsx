import { Navigate, Route, Routes } from 'react-router-dom';

import { AppLayout } from '@/components/AppLayout';
import { AnalyticsScreen } from '@/screens/AnalyticsScreen';
import { CaptureScreen } from '@/screens/CaptureScreen';
import { CollectionScreen } from '@/screens/CollectionScreen';
import { InboxScreen } from '@/screens/InboxScreen';
import { OnboardingScreen } from '@/screens/OnboardingScreen';
import { PrivacyScreen } from '@/screens/PrivacyScreen';
import { ProfileScreen } from '@/screens/ProfileScreen';
import { SettingsScreen } from '@/screens/SettingsScreen';
import { SubscriptionScreen } from '@/screens/SubscriptionScreen';
import { TodayScreen } from '@/screens/TodayScreen';

export function AppRoutes(): JSX.Element {
  return (
    <Routes>
      <Route path="/onboarding" element={<OnboardingScreen />} />
      <Route element={<AppLayout />}>
        <Route path="/today" element={<TodayScreen />} />
        <Route path="/inbox" element={<InboxScreen />} />
        <Route path="/inbox/:id" element={<InboxScreen />} />
        <Route path="/capture" element={<CaptureScreen />} />
        <Route path="/analytics" element={<AnalyticsScreen />} />
        <Route path="/profile" element={<ProfileScreen />} />
        <Route path="/settings" element={<SettingsScreen />} />
        <Route path="/privacy" element={<PrivacyScreen />} />
        <Route path="/subscription" element={<SubscriptionScreen />} />
        <Route path="/tasks" element={<CollectionScreen kind="tasks" />} />
        <Route path="/events" element={<CollectionScreen kind="events" />} />
        <Route path="/expenses" element={<CollectionScreen kind="expenses" />} />
        <Route path="/meals" element={<CollectionScreen kind="meals" />} />
        <Route path="/habits" element={<CollectionScreen kind="habits" />} />
        <Route path="/notes" element={<CollectionScreen kind="notes" />} />
      </Route>
      <Route path="*" element={<Navigate to="/today" replace />} />
    </Routes>
  );
}
