<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import { ArrowLeft, Check, Close } from "@element-plus/icons-vue";
import api from "@/services/api";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const projectId = route.params.id as string;
const testId = route.params.testId as string;

const loading = ref(true);
const testData = ref<any>(null);

interface AnswerDetail {
  questionId: string;
  questionText: string;
  questionType: string;
  options: string[];
  correctAnswer: any;
  studentAnswer: any;
  isCorrect: boolean | null;
  score: number | null;
  maxScore: number;
  feedback: string | null;
  gradingStatus: string;
  gradedBy: string;
}

const answers = ref<AnswerDetail[]>([]);

const loadTestDetails = async () => {
  loading.value = true;
  try {
    const response = await api.get(`/tests/${testId}/details`);
    testData.value = response.data;
    answers.value = response.data.answers || [];
  } catch (error: any) {
    console.error("Error loading test details:", error);
    ElMessage.error(error.response?.data?.detail || "Failed to load test details");
  } finally {
    loading.value = false;
  }
};

const goBack = () => {
  router.push(`/teacher/project/${projectId}/lobby`);
};

const getAnswerDisplay = (answer: AnswerDetail): string => {
  if (answer.studentAnswer === null || answer.studentAnswer === undefined) {
    return t("common.noAnswer") || "No answer";
  }
  
  if (answer.questionType === "single-choice" && answer.options) {
    const index = answer.studentAnswer;
    return answer.options[index] || `Option ${index}`;
  }
  
  if (answer.questionType === "multiple-choice" && answer.options) {
    const indices = answer.studentAnswer as number[];
    return indices.map(i => answer.options[i] || `Option ${i}`).join(", ");
  }
  
  if (answer.questionType === "true-false") {
    return answer.studentAnswer ? "True" : "False";
  }
  
  if (answer.questionType === "matching") {
    const pairs = answer.studentAnswer as any[];
    return pairs?.map(p => `${p.left} → ${p.right}`).join("; ") || "-";
  }
  
  return String(answer.studentAnswer);
};

const getCorrectDisplay = (answer: AnswerDetail): string => {
  if (answer.correctAnswer === null || answer.correctAnswer === undefined) {
    return "-";
  }
  
  if (answer.questionType === "single-choice" && answer.options) {
    const index = answer.correctAnswer;
    return answer.options[index] || `Option ${index}`;
  }
  
  if (answer.questionType === "multiple-choice" && answer.options) {
    const indices = answer.correctAnswer as number[];
    return indices.map(i => answer.options[i] || `Option ${i}`).join(", ");
  }
  
  if (answer.questionType === "true-false") {
    return answer.correctAnswer ? "True" : "False";
  }
  
  if (answer.questionType === "matching") {
    const pairs = answer.correctAnswer as any[];
    return pairs?.map(p => `${p.left} → ${p.right}`).join("; ") || "-";
  }
  
  if (answer.questionType === "short-answer") {
    const keywords = answer.correctAnswer as string[];
    return `Keywords: ${keywords?.join(", ") || "-"}`;
  }
  
  return String(answer.correctAnswer);
};

const totalScore = computed(() => {
  return answers.value.reduce((sum, a) => sum + (a.score || 0), 0);
});

const maxScore = computed(() => {
  return answers.value.reduce((sum, a) => sum + a.maxScore, 0);
});

const scorePercent = computed(() => {
  if (maxScore.value === 0) return 0;
  return Math.round((totalScore.value / maxScore.value) * 100);
});

onMounted(() => {
  loadTestDetails();
});
</script>

<template>
  <div class="test-review-view">
    <el-page-header @back="goBack">
      <template #content>
        <span class="page-title">{{ t("lobby.studentAnswers") || "Student Answers Review" }}</span>
      </template>
    </el-page-header>

    <div v-loading="loading" class="content">
      <!-- Summary Card -->
      <el-card v-if="testData" class="summary-card">
        <template #header>
          <h3>{{ t("common.summary") || "Summary" }}</h3>
        </template>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-statistic :title="t('common.student') || 'Student'">
              <template #default>
                {{ testData.studentName || testData.studentEmail }}
              </template>
            </el-statistic>
          </el-col>
          <el-col :span="6">
            <el-statistic 
              :title="t('lobby.score') || 'Score'" 
              :value="scorePercent"
              suffix="%"
            />
          </el-col>
          <el-col :span="6">
            <el-statistic 
              :title="t('common.points') || 'Points'" 
              :value="`${totalScore.toFixed(1)} / ${maxScore}`"
            />
          </el-col>
          <el-col :span="6">
            <el-statistic :title="t('lobby.testStatus') || 'Status'">
              <template #default>
                <el-tag :type="testData.status === 'completed' ? 'success' : 'warning'">
                  {{ testData.status }}
                </el-tag>
              </template>
            </el-statistic>
          </el-col>
        </el-row>
      </el-card>

      <!-- Answers List -->
      <el-card class="answers-card">
        <template #header>
          <h3>{{ t("common.answers") || "Answers" }} ({{ answers.length }})</h3>
        </template>
        
        <el-empty v-if="!loading && answers.length === 0" :description="t('common.noData') || 'No answers found'" />
        
        <div v-for="(answer, index) in answers" :key="answer.questionId" class="answer-item">
          <div class="question-header">
            <span class="question-number">{{ index + 1 }}.</span>
            <el-tag size="small" type="info">{{ answer.questionType }}</el-tag>
            <el-tag 
              size="small" 
              :type="answer.isCorrect ? 'success' : answer.isCorrect === false ? 'danger' : 'warning'"
              style="margin-left: 8px"
            >
              {{ answer.score?.toFixed(1) || 0 }} / {{ answer.maxScore }} pts
            </el-tag>
            <el-icon v-if="answer.isCorrect" class="correct-icon" color="var(--el-color-success)">
              <Check />
            </el-icon>
            <el-icon v-else-if="answer.isCorrect === false" class="incorrect-icon" color="var(--el-color-danger)">
              <Close />
            </el-icon>
          </div>
          
          <div class="question-text">{{ answer.questionText }}</div>
          
          <div class="answer-details">
            <div class="answer-row">
              <span class="label">{{ t("common.studentAnswer") || "Student's Answer" }}:</span>
              <span class="value" :class="{ correct: answer.isCorrect, incorrect: answer.isCorrect === false }">
                {{ getAnswerDisplay(answer) }}
              </span>
            </div>
            <div class="answer-row" v-if="answer.questionType !== 'essay'">
              <span class="label">{{ t("common.correctAnswer") || "Correct Answer" }}:</span>
              <span class="value correct">{{ getCorrectDisplay(answer) }}</span>
            </div>
            <div class="answer-row" v-if="answer.feedback">
              <span class="label">{{ t("common.feedback") || "Feedback" }}:</span>
              <span class="value feedback">{{ answer.feedback }}</span>
            </div>
            <div class="answer-row" v-if="answer.gradingStatus === 'pending'">
              <el-tag type="warning" size="small">
                {{ t("lobby.pendingGrading") || "Pending AI Grading" }}
              </el-tag>
            </div>
          </div>
          
          <el-divider v-if="index < answers.length - 1" />
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped lang="scss">
.test-review-view {
  padding: 20px;
  
  .page-title {
    font-size: 18px;
    font-weight: 600;
  }
  
  .content {
    margin-top: 20px;
  }
  
  .summary-card {
    margin-bottom: 20px;
  }
  
  .answers-card {
    .answer-item {
      padding: 16px 0;
      
      .question-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        
        .question-number {
          font-weight: 600;
          font-size: 16px;
        }
        
        .correct-icon, .incorrect-icon {
          margin-left: auto;
          font-size: 20px;
        }
      }
      
      .question-text {
        font-size: 15px;
        margin-bottom: 12px;
        padding: 12px;
        background: var(--el-fill-color-light);
        border-radius: 8px;
      }
      
      .answer-details {
        padding-left: 20px;
        
        .answer-row {
          display: flex;
          margin-bottom: 8px;
          
          .label {
            min-width: 140px;
            color: var(--el-text-color-secondary);
            font-size: 14px;
          }
          
          .value {
            flex: 1;
            font-size: 14px;
            
            &.correct {
              color: var(--el-color-success);
            }
            
            &.incorrect {
              color: var(--el-color-danger);
            }
            
            &.feedback {
              font-style: italic;
              color: var(--el-text-color-secondary);
            }
          }
        }
      }
    }
  }
}
</style>
