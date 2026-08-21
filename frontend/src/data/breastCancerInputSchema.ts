import type { ExtractionValueType } from '@/composables/useExtractionConfig'

export interface BreastCancerInputField {
  key: string
  label: string
  path: string
  type: ExtractionValueType
  itemType: Exclude<ExtractionValueType, 'array'>
  typeLabel: string
  sectionId: string
  sectionLabel: string
  isArraySection: boolean
  defaultSelected: boolean
}

export interface BreastCancerInputSection {
  id: string
  label: string
  path: string
  isArray: boolean
  fields: BreastCancerInputField[]
}

type ScalarType = Exclude<ExtractionValueType, 'array'>

const SECTION_FIELDS: Record<string, string[]> = {
  standard_patient: ['patient_id', 'patient_seq_no', 'patient_name', 'birthday', 'birthday_time', 'standard_gender', 'original_gender', 'nation', 'card_no_type', 'id_card_no', 'mobile', 'province', 'city', 'county', 'remark', 'service_agency', 'status', 'level', 'marital_status', 'level_enum', 'health_card_no', 'ward', 'report_from_type', 'md5'],
  laboratories: ['parent_id', 'visit_id', 'case_history_id', 'recipe_name', 'recipe_type', 'report_id', 'test_no', 'report_name', 'standard_report_name', 'report_time', 'patient_id', 'standard_group_name', 'original_group_name', 'original_group_code', 'patient_name', 'patient_seq_no', 'standard_gender', 'original_gender', 'standard_age', 'original_age', 'original_laboratory_name', 'original_laboratory_code', 'original_specimen', 'original_specimen_code', 'original_unit', 'original_abnormal_indicator', 'original_reference', 'original_result', 'original_specimen_no', 'organization_id', 'organization_name', 'department_name', 'department_code', 'apply_doctor_code', 'apply_doctor_name', 'clinical_diagnosis', 'standard_specimen', 'standard_unit', 'standard_abnormal_indicator', 'standard_abnormal_indicator_norm', 'standard_reference', 'standard_result', 'standard_result_norm', 'standard_quantitative_result', 'standard_result_type', 'standard_laboratory_id', 'standard_laboratory_name', 'standard_normalized_quantitative', 'abnormal', 'result_time', 'inspect_time', 'memo', 'specimen_collect_time', 'patient_annex_id', 'in_patient_no', 'recipe_id', 'item_id', 'item_code', 'patient_card', 'standard_scene', 'hospital_id', 'first_visit', 'last_visit', 'standard_laboratory_method', 'mutual_recognition_item_flag'],
  diagnosis: ['visit_id', 'case_history_id', 'report_id', 'report_name', 'patient_id', 'patient_name', 'patient_seq_no', 'standard_gender', 'original_gender', 'standard_age', 'original_age', 'hospital_name', 'hospital_id', 'organization_id', 'organization_name', 'standard_diagnosis_type', 'original_diagnosis_type', 'standard_diagnosis_type_error', 'diagnosis_seq_no', 'standard_report_type', 'source_type', 'standard_id', 'original_id', 'standard_name', 'original_diagnosis_name', 'original_desc_diagnosis_name', 'standard_name_error', 'department_name', 'standard_department_name', 'standard_department_name_error', 'department_code', 'report_time', 'original_diagnosis_date', 'doctor_name', 'doctor_code', 'original_doctor_code', 'destruct_group_no', 'destruct_group', 'destruct_group_original_value', 'standard_scene', 'patient_annex_id', 'postscript', 'in_patient_no', 'patient_card', 'first_visit', 'last_visit', 'diagnosis_id'],
  examine_items: ['visit_id', 'standard_examine_type', 'original_examine_type', 'report_id', 'original_report_id', 'report_name', 'original_report_name', 'standard_report_name', 'standard_report_name_error', 'report_time', 'patient_id', 'patient_name', 'patient_seq_no', 'standard_gender', 'original_gender', 'standard_age', 'original_age', 'standard_examine_id', 'original_examine_id', 'standard_item_name', 'original_item_name', 'standard_item_name_error', 'original_part_id', 'standard_part_id', 'standard_part_name_list', 'original_part_name', 'original_model_id', 'standard_model_id', 'standard_model_name_list', 'original_model_name', 'original_direction_id', 'standard_direction_id', 'standard_direction_name_list', 'original_direction_name', 'standard_description', 'abnormal_indicator', 'standard_abnormal_indicator', 'original_description', 'standard_result', 'original_result', 'struct_version', 'apply_department_code', 'apply_department_name', 'standard_apply_department_name', 'standard_apply_department_name_error', 'inspect_time', 'data_action_type', 'standard_scene', 'organization_id', 'organization_name', 'hospital_id', 'clinical_diagnosis', 'first_visit', 'last_visit', 'struct_error_code', 'struct_status', 'keyword_type', 'mutual_recognition_tag'],
  recipe_medicines: ['visit_id', 'card_no', 'case_history_id', 'in_patient_no', 'patient_id', 'patient_annex_id', 'patient_name', 'patient_seq_no', 'standard_gender', 'standard_age', 'original_gender', 'original_age', 'department_name', 'standard_department_name', 'standard_department_name_error', 'department_code', 'doctor_name', 'doctor_code', 'recipe_id', 'recipe_type', 'recipe_name', 'recipe_time', 'pay_time', 'medicine_start_time', 'medicine_end_time', 'original_cost_total', 'standard_cost_total', 'days', 'original_amount', 'standard_amount', 'recipe_unit', 'drug_form', 'dosage', 'dose_unit', 'each_quantity', 'frequency_code', 'frequency_name', 'group_id', 'medicine_class', 'medicine_code', 'original_medicine_name', 'standard_medicine_name', 'standard_medicine_name_error', 'medicine_std_code', 'packing_spec_num', 'packing_spec_unit', 'show_quantity', 'original_show_unit', 'standard_show_unit', 'original_spec', 'standard_spec', 'unit', 'original_unit_price', 'standard_unit_price', 'usage', 'usage_advice', 'usage_code', 'usage_content', 'standard_scene', 'first_visit', 'last_visit'],
  standard_outpatient_medical_records: ['visit_id', 'case_history_id', 'in_patient_no', 'patient_id', 'patient_seq_no', 'patient_name', 'original_gender', 'original_age', 'standard_gender', 'standard_age', 'outpatient_time', 'report_time', 'department_code', 'records_doctor_code', 'records_doctor_name', 'department_name', 'standard_department_name', 'standard_department_name_error', 'chief_complaint', 'medical_history', 'family_history', 'personal_history', 'menstrual_history', 'present_illness_history', 'allergy_history', 'marital_status', 'childbearing_history', 'physical_examination', 'original_diagnosis_name', 'recommendation', 'systolic_pressure', 'diastolic_pressure', 'heart_rate', 'body_temperature', 'respiration', 'ancillary_tests', 'refuse_treatment', 'in_house_ancillary_tests', 'visit_type', 'treatment_time', 'standard_scene', 'record_item_name', 'record_text', 'original_record_text', 'record_text_edit', 'documentary_id', 'documentary_type', 'finished_symptom', 'struct_version', 'hospital_name'],
  standard_inpatient_documentations: ['visit_id', 'case_history_id', 'in_patient_no', 'patient_id', 'patient_name', 'patient_seq_no', 'standard_gender', 'standard_age', 'original_gender', 'original_age', 'documentary_id', 'documentary_type', 'standard_documentary_type_list', 'standard_documentary_type_error', 'department_name', 'standard_department_name', 'standard_department_name_error', 'department_code', 'records_doctor_name', 'records_doctor_code', 'ward_code', 'ward_name', 'standard_scene', 'status', 'record_item_id', 'record_item_name', 'standard_record_item_name', 'record_text', 'record_text_edit', 'original_record_text', 'report_time', 'document_creat_time', 'document_update_time', 'chief_complaint', 'present_illness_history', 'struct_version', 'operation_struct_version', 'hospital_name', 'feature_struct_version', 'feature_struct_error_code'],
  standard_physical_sign_records: ['visit_id', 'case_history_id', 'in_patient_no', 'patient_id', 'patient_name', 'patient_seq_no', 'standard_gender', 'standard_age', 'original_gender', 'original_age', 'department_name', 'standard_department_name', 'standard_department_name_error', 'department_code', 'record_time', 'systolic_pressure', 'diastolic_pressure', 'heart_rate', 'body_temperature', 'respiration', 'body_height', 'body_weight', 'bmi', 'standard_scene', 'hospital_id', 'first_visit', 'last_visit'],
  standard_pathology_reports: ['visit_id', 'case_history_id', 'report_id', 'report_name', 'patient_id', 'patient_name', 'patient_seq_no', 'standard_gender', 'original_gender', 'standard_age', 'original_age', 'report_time', 'specimen_type', 'specimen_site', 'specimen_description', 'clinical_diagnosis', 'pathology_diagnosis', 'pathology_description', 'standard_scene', 'hospital_id', 'first_visit', 'last_visit'],
  standard_final_operation_records: ['visit_id', 'case_history_id', 'in_patient_no', 'patient_id', 'patient_name', 'patient_seq_no', 'standard_gender', 'standard_age', 'original_gender', 'original_age', 'operation_time', 'operation_name', 'standard_operation_name', 'operation_code', 'surgeon_name', 'surgeon_code', 'anesthesia_method', 'anesthesia_doctor', 'operation_description', 'operation_result', 'standard_scene', 'hospital_id', 'first_visit', 'last_visit'],
  standard_out_patient_visits: ['visit_id', 'patient_id', 'patient_name', 'patient_seq_no', 'standard_gender', 'standard_age', 'original_gender', 'original_age', 'visit_time', 'department_code', 'department_name', 'standard_department_name', 'standard_department_name_error', 'doctor_code', 'doctor_name', 'visit_type', 'chief_complaint', 'diagnosis', 'standard_scene', 'hospital_id', 'first_visit', 'last_visit'],
  standard_in_patient_records: ['visit_id', 'patient_id', 'in_patient_no', 'patient_card', 'case_history_id', 'patient_name', 'patient_seq_no', 'standard_gender', 'standard_age', 'original_gender', 'original_age', 'in_hospital_time', 'admit_department_code', 'admit_department_name', 'standard_admit_department_name', 'standard_admit_department_name_error', 'ambulatory_surgery_tab', 'inpatient_ward_code', 'inpatient_ward_name', 'bed_number', 'attending_doctor_code', 'attending_doctor_name', 'charge_nurse_code', 'charge_nurse_name', 'enter_way', 'standard_scene', 'hospital_id', 'first_visit', 'last_visit'],
}

const SECTION_LABELS: Record<string, string> = {
  standard_patient: '患者基本信息',
  laboratories: '检验结果',
  diagnosis: '诊断记录',
  examine_items: '检查项目',
  recipe_medicines: '处方用药',
  standard_outpatient_medical_records: '门诊病历',
  standard_inpatient_documentations: '住院文书',
  standard_physical_sign_records: '体征记录',
  standard_pathology_reports: '病理报告',
  standard_final_operation_records: '手术记录',
  standard_out_patient_visits: '门诊就诊记录',
  standard_in_patient_records: '住院记录',
}

const ARRAY_SECTIONS = new Set(Object.keys(SECTION_FIELDS).filter((id) => id !== 'standard_patient'))

const DEFAULT_SELECTED_FIELDS = new Set([
  'diagnosis.standard_gender',
  'diagnosis.standard_age',
  'diagnosis.standard_diagnosis_type',
  'diagnosis.standard_name',
  'laboratories.standard_group_name',
  'laboratories.standard_laboratory_name',
  'laboratories.standard_specimen',
  'laboratories.standard_unit',
  'laboratories.standard_abnormal_indicator',
  'laboratories.standard_reference',
  'laboratories.standard_result',
  'laboratories.standard_quantitative_result',
  'laboratories.standard_result_type',
  'laboratories.standard_normalized_quantitative',
  'laboratories.abnormal',
  'examine_items.standard_examine_type',
  'examine_items.standard_item_name',
  'examine_items.standard_description',
  'examine_items.standard_result',
  'examine_items.original_description',
  'examine_items.original_result',
  'standard_pathology_reports.standard_age',
  'standard_pathology_reports.standard_gender',
  'standard_pathology_reports.specimen_type',
  'standard_pathology_reports.specimen_site',
  'standard_pathology_reports.clinical_diagnosis',
  'standard_pathology_reports.pathology_diagnosis',
  'standard_pathology_reports.pathology_description',
  'standard_physical_sign_records.standard_age',
  'standard_physical_sign_records.standard_gender',
  'standard_physical_sign_records.systolic_pressure',
  'standard_physical_sign_records.diastolic_pressure',
  'standard_physical_sign_records.heart_rate',
  'standard_physical_sign_records.body_temperature',
  'standard_physical_sign_records.respiration',
  'standard_physical_sign_records.body_height',
  'standard_physical_sign_records.body_weight',
  'standard_physical_sign_records.bmi',
  'standard_inpatient_documentations.documentary_type',
  'standard_inpatient_documentations.record_item_name',
  'standard_in_patient_records.standard_age',
  'standard_in_patient_records.standard_gender',
  'standard_in_patient_records.standard_admit_department_name',
  'standard_in_patient_records.enter_way',
])

const INTEGER_FIELDS = new Set([
  'standard_patient.patient_seq_no',
  'laboratories.report_time', 'laboratories.patient_seq_no', 'laboratories.standard_age', 'laboratories.result_time', 'laboratories.specimen_collect_time',
  'diagnosis.patient_seq_no', 'diagnosis.standard_age', 'diagnosis.diagnosis_seq_no', 'diagnosis.report_time', 'diagnosis.original_diagnosis_date',
  'examine_items.report_time', 'examine_items.patient_seq_no', 'examine_items.standard_age', 'examine_items.inspect_time', 'examine_items.standard_scene',
  'standard_inpatient_documentations.patient_seq_no', 'standard_inpatient_documentations.standard_age', 'standard_inpatient_documentations.standard_scene', 'standard_inpatient_documentations.report_time', 'standard_inpatient_documentations.document_creat_time', 'standard_inpatient_documentations.document_update_time',
  'standard_physical_sign_records.patient_seq_no', 'standard_physical_sign_records.standard_age', 'standard_physical_sign_records.record_time', 'standard_physical_sign_records.systolic_pressure', 'standard_physical_sign_records.diastolic_pressure', 'standard_physical_sign_records.heart_rate', 'standard_physical_sign_records.respiration', 'standard_physical_sign_records.standard_scene', 'standard_physical_sign_records.first_visit', 'standard_physical_sign_records.last_visit',
  'standard_pathology_reports.patient_seq_no', 'standard_pathology_reports.standard_age', 'standard_pathology_reports.report_time', 'standard_pathology_reports.standard_scene', 'standard_pathology_reports.first_visit', 'standard_pathology_reports.last_visit',
  'standard_in_patient_records.patient_seq_no', 'standard_in_patient_records.standard_age', 'standard_in_patient_records.in_hospital_time', 'standard_in_patient_records.standard_scene', 'standard_in_patient_records.first_visit', 'standard_in_patient_records.last_visit',
])

const NUMBER_FIELDS = new Set(['standard_physical_sign_records.body_temperature'])

const BOOLEAN_FIELDS = new Set([
  'laboratories.abnormal',
  'diagnosis.standard_name_error', 'diagnosis.standard_department_name_error',
  'examine_items.standard_report_name_error', 'examine_items.standard_item_name_error', 'examine_items.standard_apply_department_name_error',
  'standard_physical_sign_records.standard_department_name_error',
  'standard_in_patient_records.standard_admit_department_name_error',
])

const TOKEN_LABELS: Record<string, string> = {
  abnormal: '异常', action: '动作', admit: '入院', advice: '建议', age: '年龄', agency: '机构', allergy: '过敏', ambulatory: '日间', amount: '数量', ancillary: '辅助检查', anesthesia: '麻醉', annex: '附件', apply: '申请', attending: '主治', bed: '床位', birthday: '出生', bmi: 'BMI', body: '身体', card: '卡', case: '病案', charge: '负责', chief: '主诉', childbearing: '生育', city: '市', class: '类别', clinical: '临床', code: '编码', collect: '采集', complaint: '主诉', content: '内容', cost: '费用', county: '区县', creat: '创建', data: '数据', date: '日期', days: '天数', department: '科室', desc: '描述', description: '描述', destruct: '拆分', diagnosis: '诊断', diastolic: '舒张', direction: '方向', doctor: '医生', document: '文书', documentary: '文书', dosage: '剂量', dose: '剂量', drug: '药品', each: '每次', edit: '编辑', end: '结束', enter: '入院方式', enum: '枚举', error: '错误', examination: '检查', examine: '检查', family: '家族', feature: '特征', finished: '完成', first: '首次', flag: '标记', form: '剂型', frequency: '频次', from: '来源', gender: '性别', group: '分组', health: '健康', heart: '心率', height: '身高', history: '史', hospital: '医院', house: '院内', id: 'ID', illness: '疾病', in: '内', indicator: '指标', inpatient: '住院', inspect: '检查', item: '项目', keyword: '关键词', laboratory: '检验', last: '末次', level: '等级', list: '列表', marital: '婚姻', md5: 'MD5', medical: '医疗', medicine: '药品', memo: '备注', menstrual: '月经', method: '方法', mobile: '手机', model: '模式', mutual: '互认', name: '名称', nation: '民族', no: '编号', norm: '规范', normalized: '标准化', num: '序号', number: '数量', nurse: '护士', operation: '手术', organization: '机构', original: '原始', outpatient: '门诊', packing: '包装', parent: '父级', part: '部位', pathology: '病理', patient: '患者', pay: '支付', personal: '个人', physical: '体征', postscript: '附言', present: '现病', pressure: '压', price: '价格', province: '省', quantitative: '定量', quantity: '数量', rate: '频率', recipe: '处方', recognition: '识别', recommendation: '建议', record: '记录', records: '记录', reference: '参考', refuse: '拒绝', remark: '备注', report: '报告', respiration: '呼吸', result: '结果', scene: '场景', seq: '序号', service: '服务', show: '显示', site: '部位', source: '来源', spec: '规格', specimen: '标本', standard: '标准', start: '开始', status: '状态', std: '标准', struct: '结构', surgeon: '术者', surgery: '手术', symptom: '症状', systolic: '收缩', tab: '标记', tag: '标签', temperature: '温度', test: '测试', tests: '检查', text: '文本', time: '时间', total: '总计', treatment: '治疗', type: '类型', unit: '单位', update: '更新', usage: '用法', value: '值', version: '版本', visit: '就诊', ward: '病区', way: '方式', weight: '体重',
}

const EXACT_LABELS: Record<string, string> = {
  patient_id: '患者 ID', patient_seq_no: '患者序号', patient_name: '患者姓名', birthday: '出生日期', birthday_time: '出生时间',
  id_card_no: '身份证号', health_card_no: '医保卡号', card_no_type: '证件类型', standard_age: '标准年龄', original_age: '原始年龄',
  standard_gender: '标准性别', original_gender: '原始性别', case_history_id: '病案号', in_patient_no: '住院号', report_id: '报告 ID',
  report_time: '报告时间', result_time: '结果时间', inspect_time: '检查时间', standard_scene: '标准场景', first_visit: '首次就诊', last_visit: '末次就诊',
  standard_name_error: '标准名称错误', standard_department_name_error: '标准科室名称错误', standard_report_name_error: '标准报告名称错误',
  standard_item_name_error: '标准项目名称错误', standard_apply_department_name_error: '标准申请科室名称错误', standard_admit_department_name_error: '标准入院科室名称错误',
  body_temperature: '体温', systolic_pressure: '收缩压', diastolic_pressure: '舒张压', heart_rate: '心率',
  pathology_diagnosis: '病理诊断', pathology_description: '病理描述', clinical_diagnosis: '临床诊断', chief_complaint: '主诉', present_illness_history: '现病史',
  standard_result: '标准结果', original_result: '原始结果', standard_quantitative_result: '标准定量结果', standard_normalized_quantitative: '标准化定量结果',
}

function labelForKey(key: string): string {
  if (EXACT_LABELS[key]) return EXACT_LABELS[key]
  return key.split('_').map((token) => TOKEN_LABELS[token] ?? '字段').join('')
}

function scalarType(sectionId: string, key: string): ScalarType {
  const compound = `${sectionId}.${key}`
  if (BOOLEAN_FIELDS.has(compound)) return 'boolean'
  if (NUMBER_FIELDS.has(compound)) return 'number'
  if (INTEGER_FIELDS.has(compound)) return 'integer'
  return 'string'
}

function typeLabel(type: ExtractionValueType, itemType: ScalarType): string {
  const labels: Record<ExtractionValueType, string> = { any: '任意', string: '文本', number: '数值', integer: '整数', boolean: '布尔', object: '对象', array: '数组' }
  return type === 'array' ? `${labels[itemType]}列表` : labels[type]
}

export const BREAST_CANCER_INPUT_SECTIONS: BreastCancerInputSection[] = Object.entries(SECTION_FIELDS).map(([id, keys]) => {
  const isArray = ARRAY_SECTIONS.has(id)
  const label = SECTION_LABELS[id] ?? id
  const path = `$.patient_data.${id}`
  return {
    id, label, path, isArray,
    fields: keys.map((key) => {
      const itemType = scalarType(id, key)
      const type: ExtractionValueType = isArray ? 'array' : itemType
      return { key, label: labelForKey(key), path: `${path}${isArray ? '[*]' : ''}.${key}`, type, itemType, typeLabel: typeLabel(type, itemType), sectionId: id, sectionLabel: label, isArraySection: isArray, defaultSelected: DEFAULT_SELECTED_FIELDS.has(`${id}.${key}`) }
    }),
  }
})

export const BREAST_CANCER_INPUT_FIELDS = BREAST_CANCER_INPUT_SECTIONS.flatMap((section) => section.fields)

function canonicalPath(path: string): string {
  return path.replace(/\[(?:\d+|\*)\]/g, '[*]')
}

export function findBreastCancerInputField(path: string): BreastCancerInputField | undefined {
  const normalized = canonicalPath(path.trim())
  return BREAST_CANCER_INPUT_FIELDS.find((field) => field.path === normalized)
}

export function breastCancerFieldLabel(path: string, fallback = ''): string {
  return findBreastCancerInputField(path)?.label ?? fallback
}

export function breastCancerFieldTypeLabel(path: string, fallback = ''): string {
  return findBreastCancerInputField(path)?.typeLabel ?? fallback
}
