import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type { FinalFeedbackInput, ListParams, PlanInput, RunInput } from "./types";

export const queryKeys = {
  health: ["health"] as const,
  examples: ["examples"] as const,
  runs: (params?: ListParams) => ["runs", params ?? {}] as const,
  run: (id: string) => ["run", id] as const,
  feedback: (params?: ListParams) => ["feedback", params ?? {}] as const,
  batches: (params?: ListParams) => ["learning-batches", params ?? {}] as const,
  candidates: (params?: ListParams) => ["learning-candidates", params ?? {}] as const,
  candidate: (id: string) => ["learning-candidate", id] as const,
  assets: ["assets"] as const,
};

export const useHealth = () => useQuery({ queryKey: queryKeys.health, queryFn: api.health, refetchInterval: 30_000, retry: 1 });
export const useExamples = () => useQuery({ queryKey: queryKeys.examples, queryFn: api.examples, staleTime: 5 * 60_000 });
export const useRuns = (params?: ListParams) => useQuery({ queryKey: queryKeys.runs(params), queryFn: () => api.runs(params) });
export const useRun = (id?: string) => useQuery({ queryKey: queryKeys.run(id ?? ""), queryFn: () => api.run(id!), enabled: Boolean(id) });
export const useFeedback = (params?: ListParams) => useQuery({ queryKey: queryKeys.feedback(params), queryFn: () => api.feedback(params) });
export const useBatches = (params?: ListParams) => useQuery({ queryKey: queryKeys.batches(params), queryFn: () => api.batches(params) });
export const useCandidates = (params?: ListParams) => useQuery({ queryKey: queryKeys.candidates(params), queryFn: () => api.candidates(params) });
export const useCandidate = (id?: string) => useQuery({ queryKey: queryKeys.candidate(id ?? ""), queryFn: () => api.candidate(id!), enabled: Boolean(id) });
export const useAssets = () => useQuery({ queryKey: queryKeys.assets, queryFn: api.assets });

export const useCreatePlan = () => useMutation({ mutationFn: (input: PlanInput) => api.createPlan(input) });

export const useCreateRun = () => {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: RunInput) => api.createRun(input),
    onSuccess: () => client.invalidateQueries({ queryKey: ["runs"] }),
  });
};

export const useSubmitFinalFeedback = (runId: string) => {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: FinalFeedbackInput) => api.submitFinalFeedback(runId, input),
    onSuccess: () => Promise.all([
      client.invalidateQueries({ queryKey: ["runs"] }),
      client.invalidateQueries({ queryKey: ["feedback"] }),
      client.invalidateQueries({ queryKey: queryKeys.run(runId) }),
    ]),
  });
};

export const useProcessPending = () => {
  const client = useQueryClient();
  return useMutation({
    mutationFn: api.processPending,
    onSuccess: () => Promise.all([
      client.invalidateQueries({ queryKey: ["learning-batches"] }),
      client.invalidateQueries({ queryKey: ["learning-candidates"] }),
      client.invalidateQueries({ queryKey: ["feedback"] }),
    ]),
  });
};

export const useCandidateDecision = (candidateId: string) => {
  const client = useQueryClient();
  const invalidate = () => Promise.all([
    client.invalidateQueries({ queryKey: queryKeys.candidate(candidateId) }),
    client.invalidateQueries({ queryKey: ["learning-candidates"] }),
    client.invalidateQueries({ queryKey: queryKeys.assets }),
  ]);
  return {
    approve: useMutation({ mutationFn: (note?: string) => api.approveCandidate(candidateId, note), onSuccess: invalidate }),
    reject: useMutation({ mutationFn: (note: string) => api.rejectCandidate(candidateId, note), onSuccess: invalidate }),
  };
};
