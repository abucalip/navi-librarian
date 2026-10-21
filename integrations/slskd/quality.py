"""Audio quality tier evaluation for slskd search results."""

import re

def quality_tier(file_record, filename, priority):
    import re
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension == "flac":
        sample_rate_value = next((
            file_record.get(key) for key in ("sampleRate", "sample_rate", "sample_rate_hz", "sampleRateHz")
            if file_record.get(key) not in (None, "")
        ), None)
        bit_depth_value = next((
            file_record.get(key) for key in ("bitDepth", "bit_depth", "bitsPerSample", "bits_per_sample")
            if file_record.get(key) not in (None, "")
        ), None)
        try:
            sample_rate_text = str(sample_rate_value or "").strip().lower().replace("khz", "").replace("hz", "").strip()
            sample_rate = float(sample_rate_text)
            if sample_rate < 1000:
                sample_rate *= 1000
        except (TypeError, ValueError):
            sample_rate = None
        try:
            bit_depth = int(bit_depth_value)
        except (TypeError, ValueError):
            bit_depth = None
        # Soulseek filenames commonly encode FLAC resolution as [24-44.1],
        # [24bit-96kHz], or [16-bit 44.1 kHz]. Parse paired bit-depth/rate
        # labels instead of relying on one spelling of "16-bit" and "kHz".
        filename_spec = re.search(
            r"(?<!\d)(16|24|32)\s*(?:bit)?\s*[-_/x ]\s*"
            r"(44(?:[.,]1)?|48|88(?:[.,]2)?|96|176(?:[.,]4)?|192)"
            r"(?:\s*k(?:hz)?)?",
            filename,
            re.I,
        )
        filename_bit_depth = int(filename_spec.group(1)) if filename_spec else None
        filename_rate = float(filename_spec.group(2).replace(",", ".")) if filename_spec else None
        if filename_rate is not None and filename_rate < 1000:
            filename_rate *= 1000
        if filename_spec:
            bit_depth = bit_depth if bit_depth is not None else filename_bit_depth
            sample_rate = sample_rate if sample_rate is not None else filename_rate
        filename_16_44 = bool(
            re.search(r"(?<!\d)16[\s_-]*bit", filename, re.I)
            and re.search(r"(?<!\d)44(?:[.,]1)?[\s_-]*k(?:hz)?", filename, re.I)
        ) or (filename_bit_depth == 16 and filename_rate == 44100)
        if (
            (bit_depth is not None and bit_depth >= 24)
            or (sample_rate is not None and sample_rate > 44100)
        ):
            tier = "flac_hires"
        elif (sample_rate == 44100 and bit_depth == 16) or filename_16_44:
            tier = "flac_16_44"
        else:
            # Unknown FLAC remains accepted as the existing fallback tier;
            # never reject a source solely because slskd omitted audio metadata.
            tier = "flac_cd"
    elif extension == "mp3":
        bitrate = file_record.get("bitRate") or file_record.get("bitrate")
        try:
            bitrate = int(bitrate)
        except (ValueError, TypeError):
            match = re.search(r"(?<!\d)(320|256|224|192|160|128)\s?kbps", filename, re.I)
            bitrate = int(match.group(1)) if match else 0
        if bitrate >= 320:
            tier = "mp3_320"
        elif 193 <= bitrate <= 319:
            tier = "mp3_193_319"
        elif bitrate == 192:
            tier = "mp3_192"
        else:
            tier = "other"
    else:
        tier = "other"
    return priority.index(tier) if tier in priority else len(priority) + 1, tier
