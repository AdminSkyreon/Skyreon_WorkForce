"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { useState } from "react";
import { DepartmentSelect, LocationSelect } from "@/components/org-pickers";
import { Badge, Button, Card, FieldError, IconButton, Input, Label, Modal, Select } from "@/components/ui";
import { toast } from "@/components/toast";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";

const stages = ["applied", "interview", "offer", "joined", "rejected"];
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function HiringPage() {
  const qc = useQueryClient();
  const today = format(new Date(), "yyyy-MM-dd");
  const [open, setOpen] = useState(false);
  const [applicantFor, setApplicantFor] = useState<string | null>(null);
  const [editingJob, setEditingJob] = useState<Job | null>(null);
  const [editingApplicant, setEditingApplicant] = useState<{ id: string; name: string; email: string } | null>(null);
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [locationId, setLocationId] = useState("");
  const [openedOn, setOpenedOn] = useState(today);
  const [jobSubmitted, setJobSubmitted] = useState(false);
  const [person, setPerson] = useState({ name: "", email: "" });
  const [applicantSubmitted, setApplicantSubmitted] = useState(false);

  const jobs = useQuery({ queryKey: ["jobs"], queryFn: () => api<Job[]>("/jobs") });

  const jobErrors = {
    title: !title.trim() ? "Job title is required" : title.trim().length > 255 ? "Max 255 characters" : "",
    openedOn: !openedOn ? "Opened date is required" : "",
  };
  const hasJobErrors = Object.values(jobErrors).some(Boolean);

  const applicantErrors = {
    name: !person.name.trim() ? "Applicant name is required" : person.name.trim().length > 255 ? "Max 255 characters" : "",
    email: !person.email.trim()
      ? "Email is required"
      : !EMAIL_RE.test(person.email.trim())
        ? "Enter a valid email address"
        : "",
  };
  const hasApplicantErrors = Object.values(applicantErrors).some(Boolean);

  function closeJobModal() {
    setOpen(false);
    setEditingJob(null);
    setJobSubmitted(false);
    create.reset();
    updateJob.reset();
  }

  function closeApplicantModal() {
    setApplicantFor(null);
    setEditingApplicant(null);
    setPerson({ name: "", email: "" });
    setApplicantSubmitted(false);
    addApplicant.reset();
    updateApplicant.reset();
  }

  const create = useMutation({
    mutationFn: () =>
      api("/jobs", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          department: department.trim(),
          location_id: locationId || null,
          opened_on: openedOn,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["jobs"] });
      toast.success("Role opened");
      closeJobModal();
    },
  });
  const updateJob = useMutation({
    mutationFn: () =>
      api(`/jobs/${editingJob?.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: title.trim(),
          department: department.trim(),
          location_id: locationId || null,
          opened_on: openedOn,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["jobs"] });
      toast.success("Role updated");
      closeJobModal();
    },
  });
  const addApplicant = useMutation({
    mutationFn: () =>
      api(`/jobs/${applicantFor}/applicants`, {
        method: "POST",
        body: JSON.stringify({ name: person.name.trim(), email: person.email.trim() }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["jobs"] });
      toast.success("Applicant added");
      closeApplicantModal();
    },
  });
  const updateApplicant = useMutation({
    mutationFn: () =>
      api(`/applicants/${editingApplicant?.id}`, {
        method: "PATCH",
        body: JSON.stringify({ name: person.name.trim(), email: person.email.trim() }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["jobs"] });
      toast.success("Applicant updated");
      closeApplicantModal();
    },
  });
  const move = useMutation({
    mutationFn: ({ id, stage }: { id: string; stage: string }) =>
      api(`/applicants/${id}/stage?stage=${stage}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const savingJob = editingJob ? updateJob.isPending : create.isPending;
  const savingApplicant = editingApplicant ? updateApplicant.isPending : addApplicant.isPending;

  return (
    <div className="space-y-4">
      <div className="flex justify-between">
        <p className="text-sm text-ink/60">Internal hiring pipeline — not a careers site.</p>
        <Button
          onClick={() => {
            create.reset();
            updateJob.reset();
            setJobSubmitted(false);
            setEditingJob(null);
            setTitle("");
            setDepartment("");
            setLocationId("");
            setOpenedOn(today);
            setOpen(true);
          }}
        >
          Open role
        </Button>
      </div>
      {move.error ? <p className="text-sm text-red-700">{move.error.message}</p> : null}
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
                  create.reset();
                  updateJob.reset();
                  setJobSubmitted(false);
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
                      addApplicant.reset();
                      updateApplicant.reset();
                      setApplicantSubmitted(false);
                      setEditingApplicant(applicant);
                      setPerson({ name: applicant.name, email: applicant.email });
                      setApplicantFor(job.id);
                    }}
                  />
                  <Select
                    disabled={move.isPending && move.variables?.id === applicant.id}
                    value={applicant.stage}
                    onChange={(e) => move.mutate({ id: applicant.id, stage: e.target.value })}
                  >
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
              addApplicant.reset();
              updateApplicant.reset();
              setApplicantSubmitted(false);
              setEditingApplicant(null);
              setPerson({ name: "", email: "" });
              setApplicantFor(job.id);
            }}
          >
            Add applicant
          </Button>
        </Card>
      ))}
      <Modal open={open} title={editingJob ? "Edit role" : "Open a role"} onClose={closeJobModal}>
        <div className="grid gap-3">
          <div>
            <Label>Title</Label>
            <Input
              maxLength={255}
              disabled={savingJob}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            {jobSubmitted && <FieldError message={jobErrors.title} />}
          </div>
          <DepartmentSelect value={department} onChange={setDepartment} />
          <LocationSelect value={locationId} onChange={setLocationId} />
          <div>
            <Label>Opened on</Label>
            <Input
              type="date"
              disabled={savingJob}
              value={openedOn}
              onChange={(e) => setOpenedOn(e.target.value)}
            />
            {jobSubmitted && <FieldError message={jobErrors.openedOn} />}
          </div>
          {(editingJob ? updateJob.error : create.error) ? (
            <p className="text-sm text-red-700">{(editingJob ? updateJob.error : create.error)?.message}</p>
          ) : null}
          <Button
            loading={savingJob}
            onClick={() => {
              setJobSubmitted(true);
              if (!hasJobErrors) {
                if (editingJob) updateJob.mutate();
                else create.mutate();
              }
            }}
          >
            {editingJob
              ? savingJob ? "Saving..." : "Save changes"
              : savingJob ? "Creating..." : "Create"}
          </Button>
        </div>
      </Modal>
      <Modal
        open={!!applicantFor}
        title={editingApplicant ? "Edit applicant" : "Add applicant"}
        onClose={closeApplicantModal}
      >
        <div className="grid gap-3">
          <div>
            <Label>Name</Label>
            <Input
              maxLength={255}
              disabled={savingApplicant}
              value={person.name}
              onChange={(e) => setPerson((p) => ({ ...p, name: e.target.value }))}
            />
            {applicantSubmitted && <FieldError message={applicantErrors.name} />}
          </div>
          <div>
            <Label>Email</Label>
            <Input
              type="email"
              maxLength={255}
              disabled={savingApplicant}
              value={person.email}
              onChange={(e) => setPerson((p) => ({ ...p, email: e.target.value }))}
            />
            {applicantSubmitted && <FieldError message={applicantErrors.email} />}
          </div>
          {(editingApplicant ? updateApplicant.error : addApplicant.error) ? (
            <p className="text-sm text-red-700">{(editingApplicant ? updateApplicant.error : addApplicant.error)?.message}</p>
          ) : null}
          <Button
            loading={savingApplicant}
            onClick={() => {
              setApplicantSubmitted(true);
              if (!hasApplicantErrors) {
                if (editingApplicant) updateApplicant.mutate();
                else addApplicant.mutate();
              }
            }}
          >
            {editingApplicant
              ? savingApplicant ? "Saving..." : "Save changes"
              : savingApplicant ? "Adding..." : "Add"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
