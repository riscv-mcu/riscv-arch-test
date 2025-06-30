#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

// TODO Need to customized for Nuclei RISC-V CPU
#define RVMODEL_CBZ_BLOCKSIZE 16
#define RVMODEL_CMO_BLOCKSIZE 64
#define RVMODEL_PMP_GRAIN 10
#define RVMODEL_NUM_PMPS 8

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                            \
        .align 8; .global tohost; tohost: .dword 0;                     \
        .align 8; .global fromhost; fromhost: .dword 0;                 \
        .popsection;                                                    \
        .align 8; .global begin_regstate; begin_regstate:               \
        .word 128;                                                      \
        .align 8; .global end_regstate; end_regstate:                   \
        .word 4;

//RV_COMPLIANCE_HALT
#define RVMODEL_HALT    ;\
  .option push ;\
  .option arch, +zicsr, +zifencei ; \
	fence ;\
	fence.i ;\
li x1, 1                ;\
write_tohost:           ;\
    sw x1, tohost, t2   ;\
    li a0, 0x10013000   ;\
    li a1, 4            ;\
    sw a1, 0(a0)        ;\
    j write_tohost      ;\
  .option pop

// Enable L1 I/D Cache and BPU
#define RVMODEL_BOOT    \
  .option push ;\
  .option arch, +zicsr, +zifencei ; \
	csrr a0, 0xfc2 /* mcfg_info csr */ ;\
__nuclei_enable_l1_icache: ;\
	li t0, 1<<9 /* i cache bit */ ;\
	and t0, a0, t0 ;\
	beqz t0, __nuclei_enable_l1_dcache ;\
	csrsi 0x7ca, 1<<0 /* Enable L1 I Cache */ ;\
__nuclei_enable_l1_dcache: ;\
	li t0, 1<<10 /* d cache bit */ ;\
	and t0, a0, t0 ;\
	beqz t0, __nuclei_config_misc ;\
	li t0, 1<<16 /* Enable L1 D Cache */ ;\
	csrs 0x7ca, t0 ;\
 ;\
__nuclei_config_misc: ;\
	fence ;\
	fence.i ;\
	li t0, 1<<3 ;\
	csrs 0x7d0, t0 /* Enable BPU */ ;\
	li t0, 1<<9 ;\
	csrs 0x7d0, t0 /* The value of mnvec is the same as the value of mtvec, mcause.EXCCODE of NMI is 0xfff */ ;\
	li t0, 1<<7    /* Enable Zc extension if compiler wants to use Zc extension */ ;\
#if defined(__riscv_zcmp) || defined(__riscv_zcmt) ;\
	csrs 0x7d0, t0 ;\
#else ;\
	csrc 0x7d0, t0 ;\
#endif ;\
	csrci 0x320, 0x5 /* Enable mcycle and minstret counter */;\
  .option pop

//RV_COMPLIANCE_DATA_BEGIN
#define RVMODEL_DATA_BEGIN                                              \
  RVMODEL_DATA_SECTION                                                        \
  .align 4;\
  .global begin_signature; begin_signature:

//RV_COMPLIANCE_DATA_END
#define RVMODEL_DATA_END                                                      \
.align 4;\
  .global end_signature; end_signature:

//RVTEST_IO_INIT
#define RVMODEL_IO_INIT
//RVTEST_IO_WRITE_STR
#define RVMODEL_IO_WRITE_STR(_R, _STR)
//RVTEST_IO_CHECK
#define RVMODEL_IO_CHECK()
//RVTEST_IO_ASSERT_GPR_EQ
#define RVMODEL_IO_ASSERT_GPR_EQ(_S, _R, _I)
//RVTEST_IO_ASSERT_SFPR_EQ
#define RVMODEL_IO_ASSERT_SFPR_EQ(_F, _R, _I)
//RVTEST_IO_ASSERT_DFPR_EQ
#define RVMODEL_IO_ASSERT_DFPR_EQ(_D, _R, _I)

#define RVMODEL_SET_MSW_INT

#define RVMODEL_CLEAR_MSW_INT

#define RVMODEL_CLEAR_MTIMER_INT

#define RVMODEL_CLEAR_MEXT_INT


#endif // _COMPLIANCE_MODEL_H
