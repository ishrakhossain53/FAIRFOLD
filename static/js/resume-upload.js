/* FairFold — Resume upload (page #17, REQ-FR-010).
 *
 * The browser PUTs the file straight to object storage with the presigned URL
 * that `POST /api/v1/candidates/resumes/` returns; Django never receives the
 * bytes. That makes this file the only place the upload can fail in a way the
 * server cannot see, so every step has a message the candidate can act on.
 *
 * Four calls, in order:
 *   1. POST  {uploadUrl}            -> 201 { id, status, upload: {url, method, headers} }
 *   2. PUT   {upload.url}           -> 2xx   (XHR, because fetch has no progress)
 *   3. POST  {completeUrl}          -> 200 settled | 202 scanning
 *   4. GET   {detailUrl}            -> poll while the scan runs (max ~40s)
 *
 * A replacement upload (page loaded with `?replace=<id>`) deletes the old row
 * only after the new file reaches `clean`, so a failed upload never leaves the
 * candidate with nothing.
 *
 * No framework, no build step: this file is served as-is and is listed in
 * `tailwind.config.js`'s content so utilities it toggles are compiled. With
 * JavaScript disabled it never runs, and the template's <noscript> block says so.
 */
(function () {
  "use strict";

  var root = document.querySelector("[data-resume-uploader]");
  if (!root) {
    return;
  }

  var input = root.querySelector("[data-file-input]");
  var choose = root.querySelector("[data-choose-file]");
  var dropzone = root.querySelector("[data-dropzone]");
  var progress = root.querySelector("[data-progress]");
  var bar = root.querySelector("[data-progress-bar]");
  var fill = root.querySelector("[data-progress-fill]");
  var percent = root.querySelector("[data-progress-percent]");
  var nameEl = root.querySelector("[data-progress-name]");
  var statusRegion = root.querySelector("[data-status-region]");
  var errorBox = root.querySelector("[data-error]");
  var steps = root.querySelector("[data-steps]");

  var uploadUrl = root.getAttribute("data-upload-url") || "";
  var completeUrl = root.getAttribute("data-complete-url") || "";
  var detailUrl = root.getAttribute("data-detail-url") || "";
  var maxBytes = parseInt(root.getAttribute("data-max-bytes"), 10) || 0;
  var replaceId = root.getAttribute("data-replace-id") || "";

  var token = document.querySelector('meta[name="csrf-token"]');
  var csrf = token ? token.getAttribute("content") : "";
  var busy = false;

  var POLL_INTERVAL_MS = 2000;
  var POLL_ATTEMPTS = 20;

  function megabytes(bytes) {
    return Math.round((bytes / (1024 * 1024)) * 10) / 10;
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  function clearError() {
    errorBox.textContent = "";
    errorBox.hidden = true;
  }

  function say(message) {
    statusRegion.textContent = message;
  }

  function setProgress(value) {
    var clamped = Math.max(0, Math.min(100, Math.round(value)));
    percent.textContent = clamped + "%";
    bar.setAttribute("aria-valuenow", String(clamped));
    fill.style.width = clamped + "%";
  }

  function setStep(name, state) {
    var item = steps.querySelector('[data-step="' + name + '"]');
    if (!item) {
      return;
    }
    var symbol = item.querySelector("span");
    if (!symbol) {
      return;
    }
    // Symbols, not colour alone: "✔ / ✖ / ● / ○" also read out (design.md §9).
    if (state === "done") {
      symbol.textContent = "✔";
      item.className = "text-success-ink";
    } else if (state === "failed") {
      symbol.textContent = "✖";
      item.className = "text-danger-ink";
    } else if (state === "running") {
      symbol.textContent = "●";
      item.className = "text-ink-2";
    } else {
      symbol.textContent = "○";
      item.className = "text-ink-3";
    }
  }

  function resetSteps() {
    setStep("upload", "pending");
    setStep("scan", "pending");
  }

  function csrfHeaders(extra) {
    var headers = extra || {};
    headers["X-CSRFToken"] = csrf;
    return headers;
  }

  function validate(file) {
    var name = (file.name || "").toLowerCase();
    if (name.slice(-4) !== ".pdf") {
      // The server checks libmagic, not the extension (REQ-SEC-012); this is the
      // cheap first pass that saves a round trip and a rejected row.
      return "We couldn't read this file. Upload a PDF" +
        (maxBytes ? " under " + megabytes(maxBytes) + " MB" : "") + ".";
    }
    if (maxBytes && file.size > maxBytes) {
      return "That file is " + megabytes(file.size) + " MB. The limit is " +
        megabytes(maxBytes) + " MB.";
    }
    return "";
  }

  function requestUpload(file) {
    return fetch(uploadUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: csrfHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        content_type: "application/pdf",
        file_size: file.size,
        original_filename: file.name
      })
    }).then(function (response) {
      if (response.status === 201) {
        return response.json();
      }
      return response.json().catch(function () { return {}; }).then(function (body) {
        var detail = body && body.detail;
        throw new Error(detail || "We couldn't start the upload. Try again.");
      });
    }).then(function (body) {
      if (!body || !body.upload || !body.upload.url) {
        throw new Error("We couldn't start the upload. Try again.");
      }
      return body;
    });
  }

  function putFile(target, file) {
    return new Promise(function (resolve, reject) {
      var request = new XMLHttpRequest();
      request.open("PUT", target.url, true);
      var headers = target.headers || {};
      Object.keys(headers).forEach(function (name) {
        request.setRequestHeader(name, headers[name]);
      });
      request.upload.addEventListener("progress", function (event) {
        if (event.lengthComputable) {
          setProgress((event.loaded / event.total) * 100);
        }
      });
      request.onload = function () {
        if (request.status >= 200 && request.status < 300) {
          resolve();
        } else {
          reject(new Error("The upload didn't finish. Check your connection and try again."));
        }
      };
      request.onerror = function () {
        reject(new Error("The upload didn't finish. Check your connection and try again."));
      };
      request.send(file);
    });
  }

  function completeUpload(resumeId) {
    return fetch(completeUrl.replace("{id}", resumeId), {
      method: "POST",
      credentials: "same-origin",
      headers: csrfHeaders()
    }).then(function (response) {
      if (response.ok) {
        return response.json();
      }
      return response.json().catch(function () { return {}; }).then(function (body) {
        var detail = body && body.detail;
        throw new Error(detail || "We couldn't check the file. Try again.");
      });
    });
  }

  function pollScan(resumeId, attempt) {
    return fetch(detailUrl.replace("{id}", resumeId), {
      credentials: "same-origin",
      headers: { "Accept": "application/json" }
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("The check is taking longer than expected. Refresh the page.");
      }
      return response.json();
    }).then(function (body) {
      if (body.status === "rejected") {
        return body;
      }
      if (body.status === "clean") {
        return body;
      }
      if (attempt >= POLL_ATTEMPTS) {
        say("The virus check is still running. Refresh this page in a moment.");
        return body;
      }
      return new Promise(function (resolve) {
        setTimeout(resolve, POLL_INTERVAL_MS);
      }).then(function () {
        return pollScan(resumeId, attempt + 1);
      });
    });
  }

  function reloadAfter(message) {
    say(message);
    // The list is server-rendered and authoritative: reloading shows the new
    // row with its real status and, for a rejection, the reason from the API.
    setTimeout(function () { window.location.reload(); }, 1800);
  }

  function removeOldResume(resumeId) {
    if (!replaceId) {
      return Promise.resolve(true);
    }
    return fetch(detailUrl.replace("{id}", replaceId), {
      method: "DELETE",
      credentials: "same-origin",
      headers: csrfHeaders()
    }).then(function (response) {
      return response.ok || response.status === 404;
    }).catch(function () {
      return false;
    }).then(function (removed) {
      if (!removed) {
        showError(
          "The new resume is ready, but the old one couldn't be removed. " +
          "Delete it from the list below."
        );
      }
      return removed;
    });
  }

  function finish(resumeId, body) {
    if (body && body.status === "rejected") {
      setStep("scan", "failed");
      var reason = body.status_reason ? " " + body.status_reason + "." : "";
      showError("This file was rejected." + reason);
      say("Rejected. The list below will show why.");
      busy = false;
      return;
    }

    if (!body || body.status !== "clean") {
      // Still `scanning` when the poll budget ran out. Do not claim success: the
      // list is the only place that knows the real state, and a reload now would
      // show "Checking for viruses" again with no explanation.
      say("The virus check is still running. Refresh this page in a moment.");
      busy = false;
      return;
    }

    setStep("scan", "done");
    removeOldResume(resumeId).then(function () {
      reloadAfter("Ready. Reloading the list…");
    });
  }

  function start(file) {
    if (busy) {
      return;
    }

    var problem = validate(file);
    if (problem) {
      showError(problem);
      return;
    }

    busy = true;
    clearError();
    resetSteps();
    nameEl.textContent = file.name;
    progress.hidden = false;
    setProgress(0);
    say("Requesting an upload link…");
    setStep("upload", "running");

    requestUpload(file).then(function (body) {
      setStep("upload", "running");
      say("Uploading…");
      return putFile(body.upload, file).then(function () {
        setProgress(100);
        setStep("upload", "done");
        setStep("scan", "running");
        say("Uploaded. Checking for viruses…");
        return completeUpload(body.id);
      }).then(function (result) {
        return { id: body.id, result: result };
      });
    }).then(function (state) {
      if (state.result && state.result.status === "scanning") {
        return pollScan(state.id, 0).then(function (final) {
          return { id: state.id, result: final };
        });
      }
      return state;
    }).then(function (state) {
      finish(state.id, state.result || {});
    }).catch(function (error) {
      busy = false;
      progress.hidden = true;
      resetSteps();
      showError(error && error.message ? error.message : "Something went wrong. Try again.");
    });
  }

  choose.addEventListener("click", function () {
    input.click();
  });

  input.addEventListener("change", function () {
    if (input.files && input.files.length) {
      start(input.files[0]);
    }
  });

  ["dragenter", "dragover"].forEach(function (name) {
    dropzone.addEventListener(name, function (event) {
      event.preventDefault();
      dropzone.classList.add("border-primary");
    });
  });

  ["dragleave", "drop"].forEach(function (name) {
    dropzone.addEventListener(name, function (event) {
      event.preventDefault();
      dropzone.classList.remove("border-primary");
    });
  });

  dropzone.addEventListener("drop", function (event) {
    var files = event.dataTransfer ? event.dataTransfer.files : null;
    if (files && files.length) {
      start(files[0]);
    }
  });
})();
