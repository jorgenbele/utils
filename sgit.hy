#!/usr/bin/env hy
;; -*- mode: hy -*-
;; File: sgit.hy
;; Author: Jørgen Bele Reinfjell
;; Date: 30.06.2019 [dd.mm.yyyy]
;; Description: Reimplementation of sgit.py in hylang.

(require [hy.extra.anaphoric [*]])

(import [os [environ path :as os-path]]
        [pathlib [Path]]
        [sh [git ssh rsync sh]]
        [docopt [docopt]])

(setv usage-msg
      f"sgit
Usage:
  sgit [options] init <repo_name>
  sgit [options] copy <repo_path> [<repo_name>]
  sgit [options] remote [-t <track_branch>] <remote_name> <repo_path> [<repo_name>]
  sgit [options] clone <repo_name> [<repo_path>]

  sgit --help

Commands:
  init    Initialize an empty bare repo at the host (no copying)

  copy    Only copy the local repository to remote as
          a bare repo [init + copy]

  remote  Sets the remote url for remote <remote_name> (eg. origin)
          for the local repo at <repo_path> to point to repo at remote host.

  clone   Clone a repository from the remote with name <repo_name>
          to <repo_path> (or a directory <repo_name> in the current dir)

Options:
  --help  Display this help message
  -v --verbose  Enable verbose logging

Remote options:
  -h --host <host>
  -u --user <user>
  -P --port <port>
  -p --path <path>

Environment variables:
  The following environment variables can be used instead
  of the remote options flags. Environment variables are
  overridden by any cli options.

  SGIT_HOST
  SGIT_USER
  SGIT_PORT
  SGIT_PATH
  SGIT_VERBOSE
")

(defn getenv [name &optional [default None]]
  (.get environ name :default default))

;; TODO: Change user to git
(setv host None)
(setv user (getenv "USER"))
(setv port "22")
(setv path f"/home/{user}/git")
(setv debug False)


(defn pwd []
  (getenv "PWD"))

(defn build-path [base &rest other]
  (.absolute (.joinpath (Path base) (unpack-iterable other))))

(defn build-remote-path [repo-name]
  (str (.absolute (build-path path (+ repo-name ".git")))))

(defn build-rsync-path [repo-name]
  (+ user "@" host ":" (build-remote-path repo-name)))

(defn ssh-exec [command]
  (ssh "-p" port (+ user "@" host) command))

(defn clone [repo-name &optional repo-path]
  "Clone a repository at remote to local repo at repo-path"
  (when (none? repo-path)
    (setv repo-path (build-path (pwd) repo-name)))
  (setv repo-url (build-ssh-host repo-name))
  (print ":: Cloning" repo-url "into" repo-path)
  (git "clone" repo-url repo-path))

(defn copy [repo-path &optional repo-name]
  (when (none? repo-name)
    (setv repo-name (.basename os-path repo-path)))
  (debug-print repo-name)

  (setv rsync-remote-path (build-rsync-path repo-name)
        remote-path (build-remote-path repo-name))

  (print ":: Copying repo" repo-name "at" repo-path "to" rsync-remote-path)
  (rsync "-urav" (+ (str (build-path repo-path)) "/.git/") rsync-remote-path)

  (print ":: Changing remote repository type to bare")
  (ssh-exec f"cd '{remote-path}' && git config --bool core.bare true > /dev/null"))

(defn init [repo-name]
  (setv rsync-remote-path (build-rsync-path repo-name)
        remote-path (build-remote-path repo-name))

  (print ":: Initializing remote repo" repo-name "at" rsync-remote-path)
  (ssh-exec f"mkdir -p '{remote-path}' && cd '{remote-path}' && git init"))

(defn remote [remote-name repo-path &optional repo-name [track-branch None]]
  (when (none? repo-name)
    (setv repo-name (.basename os-path repo-path)))
  (debug-print repo-name)

  (setv rsync-remote-path (build-rsync-path repo-name)
        remote-path (build-remote-path repo-name))

  (print f":: Adding remote {remote-name} to " repo-name "at" repo-path "pointing to" rsync-remote-path)
  (if-not (none? track-branch)
          (sh "-c" f"cd '{repo-path}' && git remote add -t '{track-branch}' '{remote-name}' '{rsync-remote-path}'")
          (sh "-c" f"cd '{repo-path}' && git remote add '{remote-name}' '{rsync-remote-path}'")))

(defn list []
  (print ":: List of repos at remote" repo-name "at" rsync-remote-path)
  (ssh-exec f"mkdir -p '{remote-path}' && cd '{remote-path}' && git init"))

(defmacro get-and-set-arg [args args-name global-var env-var]
  "Set the global argument variable from dict key and
   global symbol or from environment variable"
  (setv arg-val (gensym))
  `(as-> (.get ~args ~args-name) ~arg-val
         (if (none? ~arg-val)
             (unless (none? (getenv ~env-var))
               (assoc (globals) ~global-var (getenv ~env-var)))
             (assoc (globals) ~global-var ~arg-val))))

(defn get-and-set-args [args pairs]
  (for [[n g e] pairs]
    (get-and-set-arg args n g e)))

(defn debug-print [&rest args]
  (when debug
    (print args)))

(defmain [&rest args]
  (setv args (docopt usage-msg))

  (get-and-set-args args [["--host"    'host  "SGIT_HOST"]
                          ["--user"    'user  "SGIT_USER"]
                          ["--path"    'path  "SGIT_PATH"]
                          ["--port"    'port  "SGIT_PORT"]
                          ["--verbose" 'debug "SGIT_VERBOSE"]])

  (debug-print args)
  (debug-print host user port path)

  (setv repo-name   (.get args "<repo_name>")
        repo-path   (.get args "<repo_path>")
        remote-name (.get args "<remote_name>")
        track-branch (.get args "<track-branch>"))


  (if (= "." repo-path)
      (setv repo-path (pwd)))

  (cond
    [(get args "clone")  (clone repo-name repo-path)]
    [(get args "copy")   (copy  repo-path repo-name)]
    [(get args "init")   (init  repo-name)]
    [(get args "remote")
     (if (none? repo-name)
         (remote remote-name repo-path :track-branch track-branch)
         (remote remote-name repo-path repo-name :track-branch track-branch))]))
