import { Navigate, Route, Routes } from 'react-router-dom';

import { AppLayout } from '@/components/AppLayout';
import { AnalyticsScreen } from '@/screens/AnalyticsScreen';
import { CaptureScreen } from '@/screens/CaptureScreen';
import { CollectionScreen } from '@/screens/CollectionScreen';
import { EventsScreen } from '@/screens/EventsScreen';
import { ExpensesScreen } from '@/screens/ExpensesScreen';
import { InboxScreen } from '@/screens/InboxScreen';
import { MealsScreen } from '@/screens/MealsScreen';
import { NotesScreen } from '@/screens/NotesScreen';
import { OnboardingScreen } from '@/screens/OnboardingScreen';
import { PrivacyScreen } from '@/screens/PrivacyScreen';
import { ProfileScreen } from '@/screens/ProfileScreen';
import { SettingsScreen } from '@/screens/SettingsScreen';
import { SubscriptionScreen } from '@/screens/SubscriptionScreen';
import { TasksScreen } from '@/screens/TasksScreen';
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
        <Route path="/tasks" element={<TasksScreen />} />
        <Route path="/notes" element={<NotesScreen />} />
        <Route path="/events" element={<EventsScreen />} />
        <Route path="/expenses" element={<ExpensesScreen />} />
        <Route path="/meals" element={<MealsScreen />} />
        <Route path="/habits" element={<CollectionScreen kind="habits" />} />
      </Route>
      <Route path="*" element={<Navigate to="/today" replace />} />
    </Routes>
  );
}
