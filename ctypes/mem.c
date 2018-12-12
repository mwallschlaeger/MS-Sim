/*
 *  Create allocations using memfd_create, ftruncate and mmap
 */
static void stress_memfd_allocs(
	const args_t *args,
	const size_t memfd_bytes,
	const uint32_t memfd_fds)
{
	int fds[memfd_fds];
	void *maps[memfd_fds];
	uint64_t i;
	const size_t page_size = args->page_size;
	const size_t min_size = 2 * page_size;
	size_t size = memfd_bytes / memfd_fds;

	if (size < min_size)
		size = min_size;

	do {
		for (i = 0; i < memfd_fds; i++) {
			fds[i] = -1;
			maps[i] = MAP_FAILED;
		}

		for (i = 0; i < memfd_fds; i++) {
			char filename[PATH_MAX];

			(void)snprintf(filename, sizeof(filename), "memfd-%u-%" PRIu64, args->pid, i);
			fds[i] = shim_memfd_create(filename, 0);
			if (fds[i] < 0) {
				switch (errno) {
				case EMFILE:
				case ENFILE:
					break;
				case ENOMEM:
					goto clean;
				case ENOSYS:
				case EFAULT:
				default:
					pr_err("%s: memfd_create failed: errno=%d (%s)\n",
						args->name, errno, strerror(errno));
					g_keep_stressing_flag = false;
					goto clean;
				}
			}
			if (!g_keep_stressing_flag)
				goto clean;
		}

		for (i = 0; i < memfd_fds; i++) {
			ssize_t ret;
#if defined(FALLOC_FL_PUNCH_HOLE) && defined(FALLOC_FL_KEEP_SIZE)
			size_t whence;
#endif

			if (fds[i] < 0)
				continue;

			if (!g_keep_stressing_flag)
				break;

			/* Allocate space */
			ret = ftruncate(fds[i], size);
			if (ret < 0) {
				switch (errno) {
				case EINTR:
					break;
				default:
					pr_fail_err("ftruncate");
					break;
				}
			}
			/*
			 * ..and map it in, using MAP_POPULATE
			 * to force page it in
			 */
			maps[i] = mmap(NULL, size, PROT_WRITE,
				MAP_FILE | MAP_SHARED | MAP_POPULATE,
				fds[i], 0);
			mincore_touch_pages(maps[i], size);
			madvise_random(maps[i], size);

#if defined(FALLOC_FL_PUNCH_HOLE) && defined(FALLOC_FL_KEEP_SIZE)
			/*
			 *  ..and punch a hole
			 */
			whence = (mwc32() % size) & ~(page_size - 1);
			ret = shim_fallocate(fds[i], FALLOC_FL_PUNCH_HOLE |
				FALLOC_FL_KEEP_SIZE, whence, page_size);
			(void)ret;
#endif
			if (!g_keep_stressing_flag)
				goto clean;
		}

		for (i = 0; i < memfd_fds; i++) {
			if (fds[i] < 0)
				continue;
#if defined(SEEK_SET)
			if (lseek(fds[i], (off_t)size>> 1, SEEK_SET) < 0) {
				if (errno != ENXIO)
					pr_fail_err("lseek SEEK_SET on memfd");
			}
#endif
#if defined(SEEK_CUR)
			if (lseek(fds[i], (off_t)0, SEEK_CUR) < 0) {
				if (errno != ENXIO)
					pr_fail_err("lseek SEEK_CUR on memfd");
			}
#endif
#if defined(SEEK_END)
			if (lseek(fds[i], (off_t)0, SEEK_END) < 0) {
				if (errno != ENXIO)
					pr_fail_err("lseek SEEK_END on memfd");
			}
#endif
#if defined(SEEK_HOLE)
			if (lseek(fds[i], (off_t)0, SEEK_HOLE) < 0) {
				if (errno != ENXIO)
					pr_fail_err("lseek SEEK_HOLE on memfd");
			}
#endif
#if defined(SEEK_DATA)
			if (lseek(fds[i], (off_t)0, SEEK_DATA) < 0) {
				if (errno != ENXIO)
					pr_fail_err("lseek SEEK_DATA on memfd");
			}
#endif
			if (!g_keep_stressing_flag)
				goto clean;
		}
clean:
		for (i = 0; i < memfd_fds; i++) {
			if (maps[i] != MAP_FAILED)
				(void)munmap(maps[i], size);
			if (fds[i] >= 0)
				(void)close(fds[i]);
		}
		inc_counter(args);
	} while (keep_stressing());
}