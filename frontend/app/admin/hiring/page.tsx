"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { DepartmentSelect, LocationSelect } from "@/components/org-pickers";
import { Badge, Button, Card, IconButton, Input, Label, Modal, Select } from "@/components/ui";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";

const stages = ["applied", "interview", "offer", "joined", "rejected"];

export default function HiringPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [applicantFor, setApplicantFor] = useState<string | null>(null);
  const [editingJob, setEditingJob] = useState<Job | null>(null);
  const [editingApplicant, setEditingApplicant] = useState<{ id: string; name: string; email: string } | null>(null);
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [locationId, setLocationId] = useState("");
  const [openedOn, setOpenedOn] = useState(new Date().toISOString().slice(0, 10));
  const [person, setPerson] = useState({ name: "", email: "" });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: () => api<Job[]>("/jobs") });
  const create = useMutation({
    mutationFn: () =>
      api("/jobs", {
        method: "POST",
        body: JSON.stringify({ title, department, location_id: locationId || null, opened_on: openedOn }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["jobs"] });
      setOpen(false);
      setEditingJob(null);
    },
  });
  const updateJob = useMutation({
    mutationFn: () =>
      api(`/jobs/${editingJob?.id}`, {
        method: "PATCH",
        body: JSON.stringify({ title, department, location_id: locationId || null, opened_on: openedOn }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["jobs"] });
      setOpen(false);
      setEditingJob(null);
    },
  });
  const addApplicant = useMutation({
    mutationFn: () => api(`/jobs/${applicantFor}/applicants`, { method: "POST", body: JSON.stringify(person) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["jobs"] });
      setApplicantFor(null);
      setEditingApplicant(null);
      setPerson({ name: "", email: "" });
    },
  });
  const updateApplicant = useMutation({
    mutationFn: () =>
      api(`/applicants/${editingApplicant?.id}`, {
        method: "PATCH",
        body: JSON.stringify(person),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["jobs"] });
      setApplicantFor(null);
      setEditingApplicant(null);
      setPerson({ name: "", email: "" });
    },
  });
  const move = useMutation({
    mutationFn: ({ id, stage }: { id: string; stage: string }) =>
      api(`/applicants/${id}/stage?stage=${stage}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between">
        <p className="text-sm text-ink/60">Internal hiring pipeline — not a careers site.</p>
        <Button
          onClick={() => {
            setEditingJob(null);
            setTitle("");
            setDepartment("");
            setLocationId("");
            setOpenedOn(new Date().toISOString().slice(0, 10));
            setOpen(true);
          }}
        >
          Open role
        </Button>
      </div>
      {jobs.data?.map((job) => (
        <Card key={job.id}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-display text-2xl">{job.title}</p>
              <p className="text-sm text-ink/50">{job.department || "No department"} · opened {job.opened_on}</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone={job.is_open ? "good" : "default"}>{job.is_open ? "Open" : "Closed"}</Badge>
              <IconButton
                label="Edit role"
                onClick={() => {
                  setEditingJob(job);
                  setTitle(job.title);
                  setDepartment(job.department || "");
                  setLocationId(job.location_id || "");
                  setOpenedOn(job.opened_on);
                  setOpen(true);
                }}
              />
            </div>
          </div>
          <div className="mt-4 space-y-2">
            {job.applicants.map((applicant) => (
              <div key={applicant.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-mist px-3 py-2">
                <div>
                  <p className="font-semibold">{applicant.name}</p>
                  <p className="text-xs text-ink/50">{applicant.email}</p>
                </div>
                <div className="flex items-center gap-2">
                <IconButton
                  label="Edit applicant"
                  onClick={() => {
                    setEditingApplicant(applicant);
                    setPerson({ name: applicant.name, email: applicant.email });
                    setApplicantFor(job.id);
                  }}
                />
                <Select value={applicant.stage} onChange={(e) => move.mutate({ id: applicant.id, stage: e.target.value })}>
                  {stages.map((stage) => (
                    <option key={stage} value={stage}>
                      {stage}
                    </option>
                  ))}
                </Select>
                </div>
              </div>
            ))}
          </div>
          <Button
            className="mt-3"
            variant="outline"
            onClick={() => {
              setEditingApplicant(null);
              setPerson({ name: "", email: "" });
              setApplicantFor(job.id);
            }}
          >
            Add applicant
          </Button>
        </Card>
      ))}
      <Modal open={open} title={editingJob ? "Edit role" : "Open a role"} onClose={() => { setOpen(false); setEditingJob(null); }}>
        <div className="grid gap-3">
          <div>
            <Label>Title</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <DepartmentSelect value={department} onChange={setDepartment} />
          <LocationSelect value={locationId} onChange={setLocationId} />
          <div>
            <Label>Opened on</Label>
            <Input type="date" value={openedOn} onChange={(e) => setOpenedOn(e.target.value)} />
          </div>
          {(editingJob ? updateJob.error : create.error) ? (
            <p className="text-sm text-red-700">{(editingJob ? updateJob.error : create.error)?.message}</p>
          ) : null}
          <Button
            loading={editingJob ? updateJob.isPending : create.isPending}
            onClick={() => (editingJob ? updateJob.mutate() : create.mutate())}
          >
            {editingJob
              ? updateJob.isPending ? "Saving..." : "Save changes"
              : create.isPending ? "Creating..." : "Create"}
          </Button>
        </div>
      </Modal>
      <Modal
        open={!!applicantFor}
        title={editingApplicant ? "Edit applicant" : "Add applicant"}
        onClose={() => {
          setApplicantFor(null);
          setEditingApplicant(null);
        }}
      >
        <div className="grid gap-3">
          <div>
            <Label>Name</Label>
            <Input value={person.name} onChange={(e) => setPerson((p) => ({ ...p, name: e.target.value }))} />
          </div>
          <div>
            <Label>Email</Label>
            <Input value={person.email} onChange={(e) => setPerson((p) => ({ ...p, email: e.target.value }))} />
          </div>
          {(editingApplicant ? updateApplicant.error : addApplicant.error) ? (
            <p className="text-sm text-red-700">{(editingApplicant ? updateApplicant.error : addApplicant.error)?.message}</p>
          ) : null}
          <Button
            loading={editingApplicant ? updateApplicant.isPending : addApplicant.isPending}
            onClick={() => (editingApplicant ? updateApplicant.mutate() : addApplicant.mutate())}
          >
            {editingApplicant
              ? updateApplicant.isPending ? "Saving..." : "Save changes"
              : addApplicant.isPending ? "Adding..." : "Add"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
