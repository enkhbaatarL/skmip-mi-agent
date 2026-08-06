import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppShell } from "./AppShell";
import { GeneratePage } from "../features/generate/GeneratePage";
import { RunDetailPage } from "../features/runs/RunDetailPage";
import { RunHistoryPage } from "../features/runs/RunHistoryPage";
import { FeedbackLedgerPage } from "../features/feedback/FeedbackLedgerPage";
import { CandidateDetailPage } from "../features/learning/CandidateDetailPage";
import { LearningPage } from "../features/learning/LearningPage";
import { NotFoundPage } from "../features/NotFoundPage";

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/generate" replace /> },
      { path: "generate", element: <GeneratePage /> },
      { path: "runs", element: <RunHistoryPage /> },
      { path: "runs/:runId", element: <RunDetailPage /> },
      { path: "feedback", element: <FeedbackLedgerPage /> },
      { path: "learning", element: <LearningPage /> },
      { path: "learning/candidates/:candidateId", element: <CandidateDetailPage /> },
      { path: "assets", element: <Navigate to="/learning?tab=assets" replace /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
