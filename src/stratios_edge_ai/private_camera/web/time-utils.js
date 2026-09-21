(function attachEdgeCameraTime(root) {
  function dateForEpoch(epochSeconds) {
    return new Date(Number(epochSeconds) * 1000);
  }

  function localDay(epochSeconds) {
    return dateForEpoch(epochSeconds).toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  }

  function localDateTime(epochSeconds) {
    return dateForEpoch(epochSeconds).toLocaleString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function localInputValue(epochSeconds) {
    const date = dateForEpoch(epochSeconds);
    const offset = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - offset).toISOString().slice(0, 16);
  }

  function epochFromLocalInput(value) {
    return new Date(value).getTime() / 1000;
  }

  function epochForInput(value, originalEpoch) {
    if (Number.isFinite(Number(originalEpoch)) && localInputValue(originalEpoch) === value) {
      return Number(originalEpoch);
    }
    return epochFromLocalInput(value);
  }

  const api = {dateForEpoch, localDay, localDateTime, localInputValue, epochFromLocalInput, epochForInput};
  root.EdgeCameraTime = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis === "undefined" ? this : globalThis);
